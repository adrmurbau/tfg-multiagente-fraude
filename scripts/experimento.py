"""
Experimento comparativo - Fase 5.

Recorre las combinaciones de modelo y modo de autoridad sobre varios lotes y
con varias repeticiones, y produce una tabla agregada con medias y
desviaciones. Convierte la observacion puntual ("el 8B descarto un fraude")
en un resultado defendible ("el 8B descarta fraude en el X% de las
ejecuciones").

Con temperature=0.1 la variabilidad es baja pero NO es cero, asi que una sola
ejecucion no demuestra nada. Por eso hay repeticiones.

Uso:
    python scripts/experimento.py                      # completo, tarda
    python scripts/experimento.py --repeticiones 2 --semillas 42 7
    python scripts/experimento.py --modelos llama3.1:8b   # solo uno

Los resultados se guardan tras CADA ejecucion, asi que si lo interrumpes no
pierdes lo hecho.
"""

import argparse
import csv
import json
import statistics
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.crew import construir_crew  # noqa: E402
from src.agents.tools import inicializar_contexto  # noqa: E402
from src.config import MODOS, REPORTS_DIR  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_lote  # noqa: E402
from src.evaluacion import auditar, medir_sistema  # noqa: E402

CAMPOS = [
    "modelo", "modo", "semilla", "repeticion", "segundos",
    "fraudes_totales", "casos_elevados", "fraudes_elevados",
    "recall_detector", "recall_sistema", "precision_sistema",
    "n_confirmados", "n_descartados",
    "n_fraude_descartado", "fraude_descartado",
    "n_descarte_correcto",
    "auditoria", "fiable", "cobertura", "error",
]


def parsear_args():
    p = argparse.ArgumentParser(description="Experimento comparativo del TFG")
    p.add_argument("--modelos", nargs="+",
                   default=["llama3.1:8b", "qwen2.5:14b"])
    p.add_argument("--modos", nargs="+", default=list(MODOS), choices=MODOS)
    p.add_argument("--semillas", nargs="+", type=int, default=[42, 7, 123])
    p.add_argument("--repeticiones", type=int, default=2,
                   help="Ejecuciones por combinacion (captura la variabilidad "
                        "del muestreo del LLM).")
    p.add_argument("--n-lote", type=int, default=500)
    p.add_argument("--fraudes", type=int, default=5)
    p.add_argument("--nucleo", action="store_true", default=True,
                   help="3 agentes en vez de 6 (por defecto, para acotar el tiempo).")
    p.add_argument("--completo", dest="nucleo", action="store_false")
    return p.parse_args()


def una_ejecucion(df, modelo, modo, semilla, repeticion, args) -> dict:
    """Ejecuta el departamento una vez y devuelve la fila de resultados."""
    lote = construir_lote(df, n=args.n_lote, n_fraudes=args.fraudes,
                          random_state=semilla)
    detector = DetectorFraude()
    inicializar_contexto(lote, detector)

    fila = {c: None for c in CAMPOS}
    fila.update(modelo=modelo, modo=modo, semilla=semilla, repeticion=repeticion)

    t0 = time.perf_counter()
    try:
        resultado = construir_crew(modo=modo, modelo=modelo, verbose=False,
                                   nucleo=args.nucleo).kickoff()
        fila["segundos"] = round(time.perf_counter() - t0, 1)

        informe = str(resultado)
        try:
            salidas = [t.raw for t in resultado.tasks_output]
        except AttributeError:
            salidas = [informe]
        # La penultima tarea es la del Investigador: sus veredictos son los
        # originales, los del Reportero vienen reproducidos y duplicarian.
        salida_inv = salidas[-2] if len(salidas) >= 2 else informe

        met = medir_sistema(lote, detector, salida_inv, modo)
        aud = auditar(informe, met["ids_expediente"], lote.index)

        fila.update({k: met[k] for k in [
            "fraudes_totales", "casos_elevados", "fraudes_elevados",
            "recall_detector", "recall_sistema", "precision_sistema",
            "n_confirmados", "n_descartados", "n_fraude_descartado",
            "n_descarte_correcto",
        ]})
        fila["fraude_descartado"] = ";".join(map(str, met["fraude_descartado"]))
        fila["auditoria"] = aud["veredicto"]
        fila["fiable"] = aud["fiable"]
        fila["cobertura"] = round(aud["cobertura"], 3)

    except Exception as e:
        fila["segundos"] = round(time.perf_counter() - t0, 1)
        fila["error"] = f"{type(e).__name__}: {e}"
        print(f"      [FALLO] {fila['error']}")
        traceback.print_exc(limit=2)

    return fila


def agregar(filas) -> str:
    """Tabla en Markdown con media y desviacion por combinacion."""
    validas = [f for f in filas if not f["error"]]
    if not validas:
        return "_Ninguna ejecucion valida._"

    combos = {}
    for f in validas:
        combos.setdefault((f["modelo"], f["modo"]), []).append(f)

    lineas = [
        "| Modelo | Modo | n | Recall detector | Recall sistema | "
        "Fraude descartado | Informes fiables | Tiempo medio |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (modelo, modo), fs in sorted(combos.items()):
        n = len(fs)
        rd = [f["recall_detector"] for f in fs]
        rs = [f["recall_sistema"] for f in fs]
        fd = sum(f["n_fraude_descartado"] for f in fs)
        fiables = sum(1 for f in fs if f["fiable"])
        seg = [f["segundos"] for f in fs]

        def mstd(v):
            m = statistics.mean(v)
            s = statistics.stdev(v) if len(v) > 1 else 0.0
            return f"{m:.3f} ± {s:.3f}"

        lineas.append(
            f"| `{modelo}` | {modo} | {n} | {mstd(rd)} | {mstd(rs)} | "
            f"{fd} | {fiables}/{n} | {statistics.mean(seg):.0f}s |"
        )
    return "\n".join(lineas)


def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = REPORTS_DIR / f"experimento_{sello}.csv"
    md_path = REPORTS_DIR / f"experimento_{sello}.md"

    total = (len(args.modelos) * len(args.modos)
             * len(args.semillas) * args.repeticiones)
    print("=" * 66)
    print("  EXPERIMENTO COMPARATIVO - Fase 5")
    print("=" * 66)
    print(f"  Modelos      : {args.modelos}")
    print(f"  Modos        : {args.modos}")
    print(f"  Semillas     : {args.semillas}")
    print(f"  Repeticiones : {args.repeticiones}")
    print(f"  TOTAL        : {total} ejecuciones")
    print(f"  Estimacion   : ~{total * 0.7:.0f} min\n")

    df = cargar_dataset()
    filas, i = [], 0

    for modelo in args.modelos:
        for modo in args.modos:
            for semilla in args.semillas:
                for rep in range(1, args.repeticiones + 1):
                    i += 1
                    print(f"  [{i:>3}/{total}] {modelo:<16} {modo:<11} "
                          f"semilla={semilla:<4} rep={rep}", flush=True)

                    fila = una_ejecucion(df, modelo, modo, semilla, rep, args)
                    filas.append(fila)

                    if not fila["error"]:
                        aviso = ""
                        if fila["n_fraude_descartado"]:
                            aviso = (f"  <-- DESCARTA FRAUDE: "
                                     f"{fila['fraude_descartado']}")
                        print(f"          recall {fila['recall_sistema']:.2f} | "
                              f"{fila['auditoria']} | "
                              f"{fila['segundos']:.0f}s{aviso}")

                    # Guardado incremental: una interrupcion no pierde nada
                    with csv_path.open("w", newline="", encoding="utf-8") as fh:
                        w = csv.DictWriter(fh, fieldnames=CAMPOS)
                        w.writeheader()
                        w.writerows(filas)

    tabla = agregar(filas)
    fallos = sum(1 for f in filas if f["error"])

    md_path.write_text(
        f"# Experimento comparativo — {sello}\n\n"
        f"- Ejecuciones: {len(filas)} ({fallos} con error)\n"
        f"- Lote: {args.n_lote} transacciones, {args.fraudes} fraudes\n"
        f"- Agentes: {'3 (nucleo)' if args.nucleo else '6 (completo)'}\n"
        f"- Semillas: {args.semillas} · Repeticiones: {args.repeticiones}\n\n"
        f"## Resultados\n\n{tabla}\n\n"
        "**Recall detector**: fraude que la capa 1 eleva a revision. Es el "
        "techo del sistema.\n\n"
        "**Recall sistema**: fraude que sobrevive a la capa 2. En modo "
        "`interpreta` coincide con el anterior por construccion; en modo "
        "`revisa` puede ser menor, nunca mayor.\n\n"
        "**Fraude descartado**: casos de fraude autentico que el Investigador "
        "retiro del informe. Cada uno es un fallo del sistema que el detector "
        "no habia cometido.\n\n"
        f"## Datos completos\n\n`{csv_path.name}`\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 66)
    print("  RESULTADOS")
    print("=" * 66 + "\n")
    print(tabla)
    print(f"\n  CSV -> {csv_path}")
    print(f"  Tabla -> {md_path}")
    if fallos:
        print(f"  AVISO: {fallos} ejecuciones fallaron; revisa la columna 'error'.")


if __name__ == "__main__":
    main()
