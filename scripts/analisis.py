"""
Analisis estadistico del experimento - Fase 5.

Toma el CSV que genera experimento.py y produce los contrastes que hacen
defendible la comparacion. Sin esto, la tabla de medias es una observacion;
con esto, es un resultado.

Dos contrastes, porque responden a preguntas distintas:

  Fisher exacto  -> ¿descarta un modelo fraude con mas frecuencia que el otro?
                    Variable binaria (hubo o no descarte erroneo), muestras
                    pequenas: es el test apropiado, no chi-cuadrado.

  Wilcoxon pareado -> dentro de un mismo modelo, ¿darle autoridad empeora el
                    recall? Las ejecuciones estan emparejadas (mismo lote,
                    misma repeticion, solo cambia el modo), asi que un test
                    pareado tiene mucha mas potencia que uno independiente.

Uso:
    python scripts/analisis.py                    # usa el CSV mas reciente
    python scripts/analisis.py reports/experimento_20260728_1153.csv
"""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import REPORTS_DIR  # noqa: E402

try:
    from scipy.stats import fisher_exact, wilcoxon
except ImportError:
    sys.exit("Falta scipy. Instala con: pip install scipy")


def cargar(ruta=None):
    if ruta:
        p = Path(ruta)
    else:
        csvs = sorted(REPORTS_DIR.glob("experimento_*.csv"))
        if not csvs:
            sys.exit("No hay ningun experimento_*.csv en reports/. "
                     "Ejecuta antes scripts/experimento.py")
        p = csvs[-1]
    filas = [f for f in csv.DictReader(p.open(encoding="utf-8")) if not f["error"]]
    return p, filas


def titulo(t):
    print(f"\n{'=' * 66}\n  {t}\n{'=' * 66}")


def main():
    ruta, filas = cargar(sys.argv[1] if len(sys.argv) > 1 else None)
    modelos = sorted({f["modelo"] for f in filas})
    lineas_md = []

    print("=" * 66)
    print("  ANALISIS ESTADISTICO DEL EXPERIMENTO")
    print("=" * 66)
    print(f"  Fichero      : {ruta.name}")
    print(f"  Ejecuciones  : {len(filas)}")
    print(f"  Modelos      : {modelos}")

    # ------------------------------------------------------------------
    titulo("1. ¿DESCARTA EL MODELO FRAUDE AUTENTICO? (modo revisa)")
    rev = [f for f in filas if f["modo"] == "revisa"]
    conteo = {}
    for m in modelos:
        rs = [f for f in rev if f["modelo"] == m]
        con = sum(1 for f in rs if int(f["n_fraude_descartado"]) > 0)
        perdidos = sum(int(f["n_fraude_descartado"]) for f in rs)
        conteo[m] = (con, len(rs))
        print(f"  {m:<16}: {con}/{len(rs)} ejecuciones con descarte erroneo "
              f"({con / max(len(rs), 1):.0%})")
        print(f"  {'':<16}  {perdidos} casos de fraude perdidos en total")

    if len(modelos) == 2:
        (a, na), (b, nb) = conteo[modelos[0]], conteo[modelos[1]]
        _, p = fisher_exact([[a, na - a], [b, nb - b]])
        veredicto = "SIGNIFICATIVO" if p < 0.05 else "NO significativo"
        print(f"\n  Test exacto de Fisher: p = {p:.4f}  ->  {veredicto} (alfa=0.05)")
        if p >= 0.05:
            print("  La diferencia observada aun podria deberse al azar. "
                  "Anade repeticiones.")
        lineas_md.append(
            f"- **Descartes erroneos** (modo revisa): "
            f"`{modelos[0]}` {a}/{na} vs `{modelos[1]}` {b}/{nb}. "
            f"Test exacto de Fisher: **p = {p:.4f}**."
        )

    # ------------------------------------------------------------------
    titulo("2. ¿DAR AUTORIDAD AL LLM EMPEORA EL RECALL? (pareado)")
    for m in modelos:
        pares = defaultdict(dict)
        for f in filas:
            if f["modelo"] == m:
                pares[(f["semilla"], f["repeticion"])][f["modo"]] = \
                    float(f["recall_sistema"])
        duplas = [(v["interpreta"], v["revisa"])
                  for v in pares.values() if len(v) == 2]
        if not duplas:
            continue

        inter = [x for x, _ in duplas]
        revi = [y for _, y in duplas]
        dif = [y - x for x, y in duplas]
        peor = sum(1 for d in dif if d < 0)

        print(f"\n  {m}")
        print(f"    recall interpreta : {statistics.mean(inter):.3f}")
        print(f"    recall revisa     : {statistics.mean(revi):.3f}")
        print(f"    empeora en        : {peor}/{len(duplas)} pares")

        if any(dif):
            _, pw = wilcoxon(dif)
            veredicto = "SIGNIFICATIVO" if pw < 0.05 else "NO significativo"
            print(f"    Wilcoxon pareado  : p = {pw:.4f}  ->  {veredicto}")
            lineas_md.append(
                f"- **`{m}`**: recall {statistics.mean(inter):.3f} "
                f"(interpreta) -> {statistics.mean(revi):.3f} (revisa), "
                f"empeora en {peor}/{len(duplas)} pares. "
                f"Wilcoxon pareado: **p = {pw:.4f}**."
            )
        else:
            print("    Sin diferencias: la capa de agentes no altera el recall.")
            lineas_md.append(
                f"- **`{m}`**: recall identico en ambos modos "
                f"({statistics.mean(inter):.3f}). La revision del LLM no "
                f"degrada la deteccion."
            )

    # ------------------------------------------------------------------
    titulo("3. REPRODUCIBILIDAD: MISMA ENTRADA, ¿MISMO RESULTADO?")
    print("  Ejecuciones con lote identico y solo variacion del muestreo del LLM.\n")
    for m in modelos:
        g = defaultdict(list)
        for f in rev:
            if f["modelo"] == m:
                g[f["semilla"]].append(float(f["recall_sistema"]))
        inestables = {s: v for s, v in g.items() if max(v) - min(v) > 0}
        print(f"  {m}: {len(inestables)}/{len(g)} lotes dan resultados distintos "
              f"entre repeticiones")
        for s, v in sorted(inestables.items(), key=lambda x: -(max(x[1]) - min(x[1]))):
            print(f"      semilla {s:<5}: {v}  (rango {max(v) - min(v):.2f})")
        if inestables:
            peor = max(max(v) - min(v) for v in inestables.values())
            lineas_md.append(
                f"- **`{m}`** no es reproducible en modo revisa: "
                f"{len(inestables)}/{len(g)} lotes producen recall distinto "
                f"entre ejecuciones identicas (rango maximo {peor:.2f})."
            )

    # ------------------------------------------------------------------
    titulo("4. FIABILIDAD DE LOS INFORMES")
    for m in modelos:
        fs = [f for f in filas if f["modelo"] == m]
        ok = sum(1 for f in fs if f["fiable"] == "True")
        print(f"  {m:<16}: {ok}/{len(fs)} informes fiables "
              f"({ok / max(len(fs), 1):.0%})")

    # ------------------------------------------------------------------
    destino = REPORTS_DIR / f"analisis_{ruta.stem.replace('experimento_', '')}.md"
    destino.write_text(
        "# Analisis estadistico del experimento\n\n"
        f"Fuente: `{ruta.name}` ({len(filas)} ejecuciones validas)\n\n"
        "## Conclusiones\n\n" + "\n".join(lineas_md) + "\n\n"
        "## Notas metodologicas\n\n"
        "- **Test exacto de Fisher** para la frecuencia de descartes erroneos: "
        "variable binaria y muestras pequenas, donde chi-cuadrado no es "
        "aplicable.\n"
        "- **Wilcoxon pareado** para el efecto del modo: las ejecuciones "
        "comparten lote y repeticion, asi que solo varia el modo. Un test "
        "pareado aprovecha esa estructura.\n"
        "- La variabilidad entre repeticiones identicas procede del muestreo "
        "del LLM (`temperature=0.1`), no de los datos: el lote y el detector "
        "son deterministas.\n",
        encoding="utf-8",
    )
    print(f"\n  Analisis guardado en {destino}")


if __name__ == "__main__":
    main()
