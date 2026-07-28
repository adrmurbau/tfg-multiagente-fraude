"""
Ejecucion end-to-end del departamento antifraude - Fase 4.

Construye un lote, se lo entrega a los seis agentes y guarda el informe que
producen. Al final contrasta el resultado con las etiquetas reales, que hasta
ese momento nadie ha visto.

Uso:
    python scripts/run_departamento.py
    python scripts/run_departamento.py --modo revisa
    python scripts/run_departamento.py --modelo qwen2.5:14b --n-lote 300
"""

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.crew import construir_crew  # noqa: E402
from src.agents.tools import inicializar_contexto  # noqa: E402
from src.agents.tools import ids_de_casos  # noqa: E402
from src.config import (  # noqa: E402
    LLM_MODEL,
    MODO_POR_DEFECTO,
    MODOS,
    REPORTS_DIR,
    TARGET_COL,
)
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_lote  # noqa: E402


def parsear_args():
    p = argparse.ArgumentParser(description="Departamento antifraude multi-agente")
    p.add_argument("--modo", choices=MODOS, default=MODO_POR_DEFECTO,
                   help="interpreta: el detector decide. revisa: el LLM puede descartar.")
    p.add_argument("--modelo", default=None, help="Modelo de Ollama a usar.")
    p.add_argument("--n-lote", type=int, default=500, help="Tamano del lote.")
    p.add_argument("--fraudes", type=int, default=5, help="Fraudes ocultos en el lote.")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--nucleo", action="store_true",
                   help="Solo Modelador -> Investigador -> Reportero. "
                        "La mitad de llamadas al LLM; util para iterar.")
    return p.parse_args()


def auditar_alucinaciones(informe: str, ids_validos: list, lote) -> str:
    """Comprueba que el informe solo habla de transacciones que existen.

    Esta auditoria nacio de un fallo real: el sistema produjo un informe
    perfectamente formateado sobre cinco transacciones inventadas, con
    importes en dolares y variables que nunca se consultaron. Un informe de
    fraude que suena bien y es falso es peor que no tener informe, porque
    nadie lo cuestiona. Desde entonces, cada ejecucion se audita.
    """
    lineas = ["", "=" * 66, "  AUDITORIA DE FIABILIDAD DEL INFORME", "=" * 66]

    # Identificadores citados. El lookaround excluye lo que forma parte de un
    # decimal (0.9989 no debe leerse como '9989') o de un nombre de variable
    # (V14 no es la transaccion 14): la primera version del auditor daba
    # falsas alarmas por eso.
    citados = {int(m) for m in re.findall(r"(?<![\w.,])(\d{1,6})(?![\w.,])", informe)}
    validos = set(ids_validos)
    universo = set(int(i) for i in lote.index)

    inventados = {c for c in citados if c not in universo}
    fuera_expediente = (citados & universo) - validos

    lineas.append(f"  Casos del expediente        : {sorted(validos)}")
    lineas.append(f"  Casos citados en el informe : {sorted(citados & universo)}")

    citados_ok = validos & citados
    lineas.append(f"  Cobertura del expediente    : "
                  f"{len(citados_ok)}/{len(validos)} casos mencionados")

    veredicto = "FIABLE"
    if inventados:
        lineas.append("")
        lineas.append(f"  [ALERTA] Numeros que no corresponden a ninguna "
                      f"transaccion del lote: {sorted(inventados)}")
        veredicto = "NO FIABLE - posible alucinacion"
    if fuera_expediente:
        lineas.append(f"  [AVISO] Cita transacciones ajenas al expediente: "
                      f"{sorted(fuera_expediente)}")
    if len(citados_ok) < len(validos):
        lineas.append(f"  [AVISO] Omite {len(validos) - len(citados_ok)} "
                      "casos del expediente.")
        if veredicto == "FIABLE":
            veredicto = "INCOMPLETO"

    if "$" in informe or "dolar" in informe.lower():
        lineas.append("  [AVISO] Menciona dolares; el dataset esta en euros.")

    # --- Auditoria semantica ---
    # La numerica no basta. En una ejecucion real el informe cito los cuatro
    # identificadores correctos y aun asi era falso, porque atribuia a las
    # transacciones un 'pais de alto riesgo' y un 'historial de actividad
    # sospechosa' que no existen en el dataset: solo hay 28 componentes PCA,
    # un importe y una hora. Ese tipo de invencion es mas dificil de detectar
    # y mas peligrosa, porque suena plausible.
    # Los patrones son deliberadamente especificos. Una primera version
    # buscaba la palabra suelta 'cuenta' y marcaba como alucinacion la
    # locucion 'tener en cuenta'. Un auditor con falsos positivos acaba
    # ignorandose, y entonces deja de proteger de nada.
    PROHIBIDOS = [
        (r"\bpa[ií]s(es)?\b", "el dataset no contiene informacion geografica"),
        (r"\bubicaci[óo]n|\bgeolocalizaci[óo]n", "no hay datos de localizacion"),
        (r"\bcomercio|\bestablecimiento|\bcomerciante", "no se identifica el comercio"),
        (r"\btitular\b", "no hay datos del titular"),
        (r"n[úu]mero de (cuenta|tarjeta)|cuenta (bancaria|del cliente)",
         "no hay identificador de cuenta ni de tarjeta"),
        (r"historial (de[l]? )?(cliente|actividad|transacciones|compras)",
         "no hay historial: cada fila es independiente"),
        (r"transacciones (anteriores|previas|recientes)",
         "no hay relacion entre transacciones"),
        (r"corto per[íi]odo|pocos minutos|en cuesti[óo]n de (minutos|segundos)",
         "no se calcula frecuencia entre transacciones"),
    ]
    bajo = informe.lower()
    inventos = [(p, m) for p, m in PROHIBIDOS if re.search(p, bajo)]
    if inventos:
        lineas.append("")
        lineas.append("  [ALERTA] Conceptos inexistentes en el dataset:")
        for patron, motivo in inventos:
            hallado = re.search(patron, bajo).group(0)
            lineas.append(f"      '{hallado}' -> {motivo}")
        veredicto = "NO FIABLE - invencion semantica"

    lineas.append("")
    lineas.append(f"  VEREDICTO DE LA AUDITORIA: {veredicto}")
    return "\n".join(lineas)


def evaluar_contra_verdad(lote, detector, informe: str, modo: str) -> str:
    """Contrasta lo que hizo el sistema con las etiquetas reales.

    Las etiquetas no se han usado en ningun momento del analisis: se abren
    aqui, igual que en un banco se sabria el desenlace despues.
    """
    puntuado = detector.puntuar(lote)
    top = detector.seleccionar_casos(lote)

    fraudes_totales = int(lote[TARGET_COL].sum())
    fraudes_en_top = int(top[TARGET_COL].sum())

    lineas = [
        "",
        "=" * 66,
        "  EVALUACION CONTRA LAS ETIQUETAS REALES",
        "=" * 66,
        f"  Fraudes reales en el lote            : {fraudes_totales}",
        f"  Casos elevados a revision            : {len(top)}",
        f"  De ellos, fraude autentico           : {fraudes_en_top}",
        f"  Precision del sistema                : {fraudes_en_top / len(top):.2f}",
        f"  Recall del sistema                   : "
        f"{fraudes_en_top / max(fraudes_totales, 1):.2f}",
        f"  Falsos negativos (fraude no elevado) : {fraudes_totales - fraudes_en_top}",
    ]

    # Los falsos negativos son la limitacion estructural del diseno: si un
    # fraude no entra en el top-N, ningun agente llega a verlo.
    perdidos = lote[(lote[TARGET_COL] == 1) & (~lote.index.isin(top.index))]
    if len(perdidos):
        lineas.append("")
        lineas.append("  Fraude que el detector NO elevo (los agentes nunca lo vieron):")
        for idx, f in perdidos.iterrows():
            prob = puntuado.loc[idx, "prob_fraude"]
            lineas.append(f"    id {idx:>4} | importe {f['Amount']:>9.2f} EUR "
                          f"| probabilidad asignada {prob:.6f}")

    if modo == "revisa":
        lineas.append("")
        lineas.append("  --- Efecto de la revision del LLM ---")
        descartados = re.findall(r"VEREDICTO:\s*DESCARTADO", informe, re.I)
        confirmados = re.findall(r"VEREDICTO:\s*CONFIRMADO", informe, re.I)
        lineas.append(f"    Casos confirmados por el investigador : {len(confirmados)}")
        lineas.append(f"    Casos descartados por el investigador : {len(descartados)}")
        if not confirmados and not descartados:
            lineas.append("    (no se han encontrado veredictos en el informe: "
                          "el modelo no siguio el formato pedido)")

    return "\n".join(lineas)


def main():
    args = parsear_args()

    print("=" * 66)
    print("  DEPARTAMENTO ANTIFRAUDE MULTI-AGENTE")
    print("=" * 66)
    print(f"  Modo   : {args.modo}")
    print(f"  Modelo : {args.modelo or LLM_MODEL}")
    print(f"  Agentes: {'3 (nucleo)' if args.nucleo else '6 (completo)'}")

    print("\n  Preparando el lote...")
    lote = construir_lote(cargar_dataset(), n=args.n_lote,
                          n_fraudes=args.fraudes, random_state=args.semilla)
    detector = DetectorFraude()
    inicializar_contexto(lote, detector)
    print(f"  {len(lote)} transacciones | "
          f"{int(lote[TARGET_COL].sum())} fraudes ocultos (nadie los ve todavia)")

    print("\n  Arrancando el departamento. Paciencia: seis agentes en local.\n")
    t0 = time.perf_counter()
    resultado = construir_crew(
        modo=args.modo, modelo=args.modelo, nucleo=args.nucleo
    ).kickoff()
    dt = time.perf_counter() - t0

    informe = str(resultado)

    print("\n" + "=" * 66)
    print("  INFORME FINAL")
    print("=" * 66)
    print(informe)
    print(f"\n  Tiempo total: {dt / 60:.1f} min")

    auditoria = auditar_alucinaciones(informe, ids_de_casos(), lote)
    print(auditoria)

    evaluacion = evaluar_contra_verdad(lote, detector, informe, args.modo)
    print(evaluacion)
    evaluacion = auditoria + "\n" + evaluacion

    REPORTS_DIR.mkdir(exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M")
    destino = REPORTS_DIR / f"informe_{args.modo}_{sello}.md"
    destino.write_text(
        f"# Informe del departamento antifraude\n\n"
        f"- Modo: `{args.modo}`\n"
        f"- Modelo: `{args.modelo or LLM_MODEL}`\n"
        f"- Lote: {len(lote)} transacciones, {int(lote[TARGET_COL].sum())} fraudes\n"
        f"- Tiempo: {dt / 60:.1f} min\n\n"
        f"---\n\n{informe}\n\n---\n\n```\n{evaluacion}\n```\n",
        encoding="utf-8",
    )
    print(f"\n  Informe guardado en {destino}")


if __name__ == "__main__":
    main()
