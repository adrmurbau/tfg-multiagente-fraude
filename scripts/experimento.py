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
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.crew import construir_crew  # noqa: E402
from src.agents.tools import inicializar_contexto, mapa_casos  # noqa: E402
from src.config import MODOS, REPORTS_DIR  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import (  # noqa: E402
    DetectorFraude,
    construir_lote,
    construir_turno,
)
from src.evaluacion import auditar, medir_sistema  # noqa: E402

CAMPOS = [
    "modelo", "modo", "semilla", "repeticion", "segundos",
    "fraudes_totales", "casos_elevados", "fraudes_elevados",
    "recall_detector", "recall_sistema", "precision_sistema",
    "n_confirmados", "n_descartados",
    "n_fraude_descartado", "fraude_descartado",
    "n_descarte_correcto",
    "auditoria", "fiable", "cobertura", "cobertura_investigacion", "error",
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
    p.add_argument("--turno-horas", type=float, default=None,
                   help="Usa ventanas temporales REALES del periodo de test. "
                        "Las semillas pasan a interpretarse como horas de "
                        "desfase del inicio del turno.")
    p.add_argument("--iterativo", action="store_true",
                   help="Una tarea de investigacion por caso, en vez de pedir "
                        "N parrafos en una sola respuesta. Garantiza cobertura "
                        "del 100%% a cambio de coste lineal.")
    p.add_argument("--capacidad", type=int, default=None,
                   help="Casos que el equipo revisa por turno.")
    p.add_argument("--nucleo", action="store_true", default=True,
                   help="3 agentes en vez de 6 (por defecto, para acotar el tiempo).")
    p.add_argument("--completo", dest="nucleo", action="store_false")
    return p.parse_args()


def calentar(modelo: str):
    """Carga el modelo en VRAM antes de cronometrar nada.

    Al cambiar de modelo, Ollama descarga el anterior y carga el nuevo. Sin
    este paso, la PRIMERA ejecucion de cada modelo carga varios GB de disco y
    el tiempo medido incluye ese coste, que no es inferencia. En la prueba
    inicial eso hacia parecer que el modo 'interpreta' era el doble de lento
    que 'revisa' cuando la unica diferencia era el orden de ejecucion.
    """
    from src.config import OLLAMA_HOST
    payload = json.dumps({
        "model": modelo, "prompt": "ping",
        "stream": False, "options": {"num_predict": 1},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_HOST}/api/generate", data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300):
            pass
    except Exception as e:
        print(f"      [aviso] no se pudo precalentar {modelo}: {e}")


def una_ejecucion(df, modelo, modo, semilla, repeticion, args) -> dict:
    """Ejecuta el departamento una vez y devuelve la fila de resultados."""
    if args.turno_horas:
        # Con turnos reales, la "semilla" es el desfase en horas del inicio
        # de la ventana dentro del periodo de test.
        lote = construir_turno(df, horas=args.turno_horas,
                               desplazamiento_h=float(semilla))
    else:
        lote = construir_lote(df, n=args.n_lote, n_fraudes=args.fraudes,
                              random_state=semilla)
    detector = DetectorFraude()
    inicializar_contexto(lote, detector, capacidad=args.capacidad)

    fila = {c: None for c in CAMPOS}
    fila.update(modelo=modelo, modo=modo, semilla=semilla, repeticion=repeticion)

    t0 = time.perf_counter()
    try:
        resultado = construir_crew(modo=modo, modelo=modelo, verbose=False,
                                   nucleo=args.nucleo,
                                   iterativo=args.iterativo).kickoff()
        fila["segundos"] = round(time.perf_counter() - t0, 1)

        informe = str(resultado)
        try:
            salidas = [t.raw for t in resultado.tasks_output]
        except AttributeError:
            salidas = [informe]
        # Con el Investigador iterativo hay N tareas de investigacion. Se unen
        # todas las salidas menos la ultima (el informe, que las reproduce).
        salida_inv = "\n\n".join(salidas[:-1]) if len(salidas) > 1 else informe

        met = medir_sistema(lote, detector, salida_inv, modo,
                            capacidad=args.capacidad, mapa_casos=mapa_casos())
        # El universo de identificadores validos son los numeros de caso
        # (1..N): cualquier otro numero citado es inventado.
        aud = auditar(informe, met["ids_expediente"], met["ids_expediente"])
        aud_inv = auditar(salida_inv, met["ids_expediente"],
                          met["ids_expediente"])
        fila["cobertura_investigacion"] = round(aud_inv["cobertura"], 3)

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

        # Si la auditoria falla, hay que poder ver POR QUE. Sin el texto solo
        # sabes que algo salio mal, no si el modelo alucino de verdad o si el
        # auditor tropezo con bloques de razonamiento.
        if not aud["fiable"]:
            fallos_dir = REPORTS_DIR / "no_fiables"
            fallos_dir.mkdir(exist_ok=True)
            nombre = f"{modelo.replace(':', '_').replace('/', '_')}_{modo}_s{semilla}_r{repeticion}.md"
            (fallos_dir / nombre).write_text(
                f"# {modelo} | {modo} | semilla {semilla} rep {repeticion}\n\n"
                f"**Auditoria:** {aud['veredicto']}\n\n"
                f"- Conceptos detectados: {aud['conceptos_inventados']}\n"
                f"- Ids inventados: {aud['ids_inventados']}\n"
                f"- Ids fuera del expediente: {aud['ids_fuera_expediente']}\n\n"
                f"---\n\n## Informe final\n\n{informe}\n\n"
                f"---\n\n## Salida del Investigador\n\n{salida_inv}\n",
                encoding="utf-8",
            )

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
        print(f"\n  Precalentando {modelo}...", flush=True)
        calentar(modelo)
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
