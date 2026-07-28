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
from src.agents.tools import inicializar_contexto  # noqa: E402
from src.config import LLM_MODEL, MODO_POR_DEFECTO, MODOS, REPORTS_DIR  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_lote  # noqa: E402
from src.evaluacion import auditar, medir_sistema  # noqa: E402


def parsear_args():
    p = argparse.ArgumentParser(description="Departamento antifraude multi-agente")
    p.add_argument("--modo", choices=MODOS, default=MODO_POR_DEFECTO,
                   help="interpreta: el detector decide. revisa: el LLM puede descartar.")
    p.add_argument("--modelo", default=None, help="Modelo de Ollama a usar.")
    p.add_argument("--n-lote", type=int, default=500, help="Tamano del lote.")
    p.add_argument("--fraudes", type=int, default=5, help="Fraudes ocultos en el lote.")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--nucleo", action="store_true",
                   help="Solo Modelador -> Investigador -> Reportero.")
    return p.parse_args()


def formatear_auditoria(aud: dict) -> str:
    L = ["", "=" * 66, "  AUDITORIA DE FIABILIDAD DEL INFORME", "=" * 66]
    L.append(f"  Casos citados del expediente : {aud['ids_cubiertos']}")
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

    L.append("")
    L.append(f"  VEREDICTO DE LA AUDITORIA: {aud['veredicto']}")
    return "\n".join(L)


def formatear_evaluacion(met: dict, lote, modo: str) -> str:
    L = ["", "=" * 66, "  EVALUACION CONTRA LAS ETIQUETAS REALES", "=" * 66]
    L.append(f"  Fraudes reales en el lote       : {met['fraudes_totales']}")
    L.append(f"  Casos elevados a revision       : {met['casos_elevados']}")
    L.append(f"  De ellos, fraude autentico      : {met['fraudes_elevados']}")
    L.append(f"  Recall del DETECTOR (capa 1)    : {met['recall_detector']:.2f}")

    if met["falsos_negativos_detector"]:
        L.append("")
        L.append("  Fraude que el detector NO elevo (los agentes nunca lo vieron):")
        for idx in met["falsos_negativos_detector"]:
            L.append(f"    id {idx:>4} | importe {lote.loc[idx, 'Amount']:>9.2f} EUR")

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

    print("\n  Preparando el lote...")
    lote = construir_lote(cargar_dataset(), n=args.n_lote,
                          n_fraudes=args.fraudes, random_state=args.semilla)
    detector = DetectorFraude()
    inicializar_contexto(lote, detector)
    print(f"  {len(lote)} transacciones | "
          f"{int(lote['Class'].sum())} fraudes ocultos (nadie los ve todavia)")

    print("\n  Arrancando el departamento. Paciencia: LLM en local.\n")
    t0 = time.perf_counter()
    resultado = construir_crew(modo=args.modo, modelo=args.modelo,
                               nucleo=args.nucleo).kickoff()
    dt = time.perf_counter() - t0

    informe = str(resultado)
    try:
        salidas = [t.raw for t in resultado.tasks_output]
    except AttributeError:
        salidas = [informe]
    # Penultima tarea = Investigador. Sus veredictos son los originales; los
    # del Reportero vienen reproducidos y duplicarian el recuento.
    salida_investigador = salidas[-2] if len(salidas) >= 2 else informe

    print("\n" + "=" * 66)
    print("  INFORME FINAL")
    print("=" * 66)
    print(informe)
    print(f"\n  Tiempo total: {dt / 60:.1f} min")

    met = medir_sistema(lote, detector, salida_investigador, args.modo)
    aud = auditar(informe, met["ids_expediente"], lote.index)

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
