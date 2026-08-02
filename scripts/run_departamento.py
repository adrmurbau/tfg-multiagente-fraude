"""
Ejecucion end-to-end del departamento antifraude - Fase 4.

Construye un lote, se lo entrega a los agentes y guarda el informe que
producen, junto con dos comprobaciones: una auditoria de fiabilidad del texto
y una evaluacion contra las etiquetas reales, que hasta ese momento nadie ha
visto.

La logica de medida vive en src/evaluacion.py, compartida con
scripts/experimento.py: asi los informes individuales y las tablas agregadas
de la memoria no pueden contradecirse.

Uso:
    python scripts/run_departamento.py
    python scripts/run_departamento.py --modo revisa
    python scripts/run_departamento.py --nucleo --modelo qwen2.5:14b
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.crew import construir_crew  # noqa: E402
from src.agents.tools import (  # noqa: E402
    NIVELES_DOSSIER,
    construir_tabla_casos,
    inicializar_contexto,
    mapa_casos,
)  # noqa: E402
from src.config import LLM_MODEL, MODO_POR_DEFECTO, MODOS, REPORTS_DIR  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import (  # noqa: E402
    DetectorFraude,
    construir_lote,
    construir_turno,
)
from src.evaluacion import auditar, medir_sistema, veredictos_por_caso  # noqa: E402


def parsear_args():
    p = argparse.ArgumentParser(description="Departamento antifraude multi-agente")
    p.add_argument("--modo", choices=MODOS, default=MODO_POR_DEFECTO,
                   help="interpreta: el detector decide. revisa: el LLM puede descartar.")
    p.add_argument("--modelo", default=None, help="Modelo de Ollama a usar.")
    p.add_argument("--n-lote", type=int, default=500, help="Tamano del lote sintetico.")
    p.add_argument("--fraudes", type=int, default=5, help="Fraudes ocultos en el lote.")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--nucleo", action="store_true",
                   help="Solo Modelador -> Investigador -> Reportero.")
    # --- Turno real (recomendado) ---
    p.add_argument("--turno-horas", type=float, default=None,
                   help="Usa una ventana temporal REAL del periodo de test en "
                        "lugar de un lote sintetico. Ej: 4 = turno de 4 horas.")
    p.add_argument("--desplazamiento", type=float, default=0.0,
                   help="Horas de desfase del inicio del turno dentro del test.")
    p.add_argument("--iterativo", action="store_true",
                   help="Una tarea de investigacion por caso, en vez de pedir "
                        "N parrafos en una sola respuesta. Garantiza cobertura "
                        "del 100%% a cambio de coste lineal.")
    p.add_argument("--capacidad", type=int, default=None,
                   help="Casos que el equipo puede revisar. Por defecto CASOS_MAX.")
    p.add_argument("--dossier", choices=NIVELES_DOSSIER, default="completo",
                   help="Informacion del detector que ve la capa 2. completo: probabilidad y "
                        "nivel de riesgo. sin_nivel: solo probabilidad. ciego: solo "
                        "contribuciones, importe y hora. Sirve para separar si el "
                        "modelo razona o copia la etiqueta de riesgo.")
    p.add_argument("--umbral", type=float, default=None,
                   help="Baja el corte de probabilidad por debajo del ALTO (0.80) "
                        "para maximizar recall. Ej: 0.05 -> mas fraude capturado "
                        "y mas falsas alarmas que la capa 2 puede filtrar.")
    return p.parse_args()


def formatear_auditoria(aud: dict) -> str:
    L = ["", "=" * 66, "  AUDITORIA DE FIABILIDAD DEL INFORME", "=" * 66]
    L.append(f"  Casos citados del expediente : {aud['ids_cubiertos']}")
    if "cobertura_investigacion" in aud:
        L.append(f"  Cobertura de la INVESTIGACION : "
                 f"{aud['cobertura_investigacion']:.0%}")
        L.append(f"  Cobertura del INFORME         : {aud['cobertura']:.0%}")
        if "cobertura_narrativa" in aud:
            L.append(f"  Cobertura del texto del modelo: "
                     f"{aud['cobertura_narrativa']:.0%}  (la tabla se ensambla aparte)")
        if aud["cobertura_investigacion"] > aud["cobertura"]:
            L.append("  >> La investigacion fue completa; el Reportero perdio "
                     "casos al sintetizar.")
    else:
        L.append(f"  Cobertura                    : {aud['cobertura']:.0%}")

    if aud["ids_inventados"]:
        L.append(f"  [ALERTA] Identificadores que no existen en el lote: "
                 f"{aud['ids_inventados']}")
    if aud["ids_fuera_expediente"]:
        L.append(f"  [AVISO] Cita transacciones ajenas al expediente: "
                 f"{aud['ids_fuera_expediente']}")
    if aud["conceptos_inventados"]:
        L.append("  [ALERTA] Conceptos inexistentes en el dataset:")
        for termino, motivo in aud["conceptos_inventados"]:
            L.append(f"      '{termino}' -> {motivo}")
    if aud["menciona_dolares"]:
        L.append("  [AVISO] Menciona dolares; el dataset esta en euros.")
    if aud.get("idioma_incorrecto"):
        L.append("  [AVISO] El informe ha derivado al INGLES pese a pedirse en "
                 "castellano.")
        L.append("          Sintoma de que el modelo ha dejado de seguir el "
                 "prompt. Revisar el entregable.")

    L.append("")
    L.append(f"  VEREDICTO DE LA AUDITORIA: {aud['veredicto']}")
    return "\n".join(L)


def formatear_evaluacion(met: dict, lote, modo: str) -> str:
    L = ["", "=" * 66, "  EVALUACION CONTRA LAS ETIQUETAS REALES", "=" * 66]
    L.append(f"  Fraudes reales en el lote       : {met['fraudes_totales']}")
    L.append(f"  Casos elevados a revision       : {met['casos_elevados']}")
    L.append(f"  De ellos, fraude autentico      : {met['fraudes_elevados']}")
    L.append(f"  Recall del DETECTOR (capa 1)    : {met['recall_detector']:.2f}")

    fn = met["falsos_negativos_detector"]
    if fn:
        L.append("")
        L.append(f"  Fraude que el detector NO elevo ({len(fn)} casos que ningun "
                 f"agente vio):")
        # Con turnos reales pueden ser decenas: se muestran los de mayor importe,
        # que son los que mas duelen, y se resume el resto.
        por_importe = sorted(fn, key=lambda i: -lote.loc[i, "Amount"])
        for idx in por_importe[:8]:
            L.append(f"    id {idx:>6} | importe {lote.loc[idx, 'Amount']:>9.2f} EUR")
        if len(fn) > 8:
            resto = sum(lote.loc[i, "Amount"] for i in por_importe[8:])
            L.append(f"    ... y {len(fn) - 8} mas, {resto:,.2f} EUR en total")
        L.append(f"    Importe total no elevado: "
                 f"{sum(lote.loc[i, 'Amount'] for i in fn):,.2f} EUR")

    if modo == "revisa":
        L.append("")
        L.append("  --- Efecto de la revision del LLM (capa 2) ---")
        L.append(f"    Casos confirmados            : {met['n_confirmados']}")
        L.append(f"    Casos descartados            : {met['n_descartados']}")
        if met["n_descarte_correcto"]:
            L.append(f"    Descartes acertados          : "
                     f"{met['descarte_correcto']} (eran falsos positivos)")
        if met["n_fraude_descartado"]:
            L.append(f"    [ALERTA] FRAUDE DESCARTADO   : {met['fraude_descartado']}")
            L.append("             El LLM retiro fraude autentico del informe.")
        if not met["n_confirmados"] and not met["n_descartados"]:
            L.append("    (sin veredictos: el modelo no siguio el formato pedido)")

    L.append("")
    L.append(f"  Recall del SISTEMA (capa 1+2)   : {met['recall_sistema']:.2f}")
    L.append(f"  Precision del SISTEMA           : {met['precision_sistema']:.2f}")
    if met["recall_sistema"] < met["recall_detector"]:
        caida = (met["recall_detector"] - met["recall_sistema"]) / met["recall_detector"]
        L.append(f"  >> La capa de agentes ha DESTRUIDO un {caida:.0%} de la "
                 f"deteccion.")
    return "\n".join(L)


def main():
    args = parsear_args()

    print("=" * 66)
    print("  DEPARTAMENTO ANTIFRAUDE MULTI-AGENTE")
    print("=" * 66)
    print(f"  Modo    : {args.modo}")
    print(f"  Modelo  : {args.modelo or LLM_MODEL}")
    print(f"  Agentes : {'3 (nucleo)' if args.nucleo else '6 (completo)'}")
    print(f"  Investigador: {'ITERATIVO (1 llamada por caso)' if args.iterativo else 'monolitico (N casos en 1 respuesta)'}")

    df = cargar_dataset()
    if args.turno_horas:
        print(f"\n  Extrayendo un turno REAL de {args.turno_horas} h "
              f"(desfase {args.desplazamiento} h)...")
        lote = construir_turno(df, horas=args.turno_horas,
                               desplazamiento_h=args.desplazamiento)
    else:
        print("\n  Preparando un lote sintetico...")
        lote = construir_lote(df, n=args.n_lote, n_fraudes=args.fraudes,
                              random_state=args.semilla)

    detector = DetectorFraude()
    inicializar_contexto(lote, detector, capacidad=args.capacidad,
                         umbral=args.umbral, dossier=args.dossier)
    print(f"  {len(lote):,} transacciones | "
          f"{int(lote['Class'].sum())} fraudes ocultos (nadie los ve todavia)")
    if args.capacidad:
        print(f"  Capacidad de revision del equipo: {args.capacidad} casos")
    if args.umbral is not None:
        print(f"  Umbral rebajado a {args.umbral} (por defecto ALTO = 0.80)")
    if args.dossier != "completo":
        print(f"  Expediente en modo '{args.dossier}': la capa 2 NO ve "
              f"{'el nivel de riesgo' if args.dossier == 'sin_nivel' else 'probabilidad ni nivel de riesgo'}")

    print("\n  Arrancando el departamento. Paciencia: LLM en local.\n")
    t0 = time.perf_counter()
    resultado = construir_crew(modo=args.modo, modelo=args.modelo,
                               nucleo=args.nucleo,
                                   iterativo=args.iterativo).kickoff()
    dt = time.perf_counter() - t0

    informe_narrativo = str(resultado)
    try:
        salidas = [t.raw for t in resultado.tasks_output]
    except AttributeError:
        salidas = [informe]
    # Con el Investigador iterativo hay N tareas de investigacion, no una. Se
    # unen TODAS las salidas menos la ultima (el informe del Reportero, que
    # reproduce los veredictos y los duplicaria en el recuento).
    salida_investigador = ("\n\n".join(salidas[:-1]) if len(salidas) > 1
                           else informe_narrativo)

    # La tabla se calcula aqui, no la escribe el modelo. Ver el docstring de
    # construir_tabla_casos: el Reportero cubria siempre unos catorce casos
    # con independencia de que el expediente tuviera 32 o 55, porque resume
    # en lugar de enumerar. Ensamblando la tabla en Python la cobertura es del
    # 100 % por construccion, y al modelo se le deja lo que sabe hacer.
    tabla = construir_tabla_casos(veredictos_por_caso(salida_investigador))
    informe = (informe_narrativo
               + "\n\n---\n\n## Casos del expediente\n\n"
               + tabla)

    print("\n" + "=" * 66)
    print("  INFORME FINAL")
    print("=" * 66)
    print(informe)
    print(f"\n  Tiempo total: {dt / 60:.1f} min")

    met = medir_sistema(lote, detector, salida_investigador, args.modo,
                        capacidad=args.capacidad, mapa_casos=mapa_casos(),
                        umbral=args.umbral)
    # El universo de identificadores validos son los numeros de caso (1..N):
    # cualquier otro numero citado es inventado.
    aud = auditar(informe, met["ids_expediente"], met["ids_expediente"])
    # La cobertura NARRATIVA -la del texto que escribe el modelo, sin la tabla
    # ensamblada- se sigue midiendo aparte: es el dato que documenta el cupo
    # del Reportero, y perderlo al arreglar el sintoma seria un error.
    aud_narrativa = auditar(informe_narrativo, met["ids_expediente"],
                            met["ids_expediente"])
    aud["cobertura_narrativa"] = aud_narrativa["cobertura"]
    # Auditoria separada de la INVESTIGACION. Si el investigador cubre el 100 %
    # y el informe no, la perdida esta en el Reportero, no en la investigacion.
    aud_inv = auditar(salida_investigador, met["ids_expediente"],
                      met["ids_expediente"])
    aud["cobertura_investigacion"] = aud_inv["cobertura"]
    aud["ids_investigados"] = aud_inv["ids_cubiertos"]

    texto_aud = formatear_auditoria(aud)
    texto_eval = formatear_evaluacion(met, lote, args.modo)
    print(texto_aud)
    print(texto_eval)

    REPORTS_DIR.mkdir(exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M")
    destino = REPORTS_DIR / f"informe_{args.modo}_{sello}.md"
    destino.write_text(
        f"# Informe del departamento antifraude\n\n"
        f"- Modo: `{args.modo}`\n"
        f"- Modelo: `{args.modelo or LLM_MODEL}`\n"
        f"- Agentes: {'3 (nucleo)' if args.nucleo else '6 (completo)'}\n"
        f"- Lote: {len(lote)} transacciones, {met['fraudes_totales']} fraudes "
        f"(semilla {args.semilla})\n"
        f"- Tiempo: {dt / 60:.1f} min\n\n"
        f"---\n\n{informe}\n\n---\n\n"
        f"```\n{texto_aud}\n{texto_eval}\n```\n",
        encoding="utf-8",
    )
    print(f"\n  Informe guardado en {destino}")


if __name__ == "__main__":
    main()
