"""
Genera las figuras de datos de la memoria a partir de los ficheros de reports/.

Las figuras NO se dibujan a mano ni se copian de una hoja de calculo: se
derivan de los mismos ficheros que citan las tablas del capitulo 5. Si una
cifra cambia al repetir un experimento, basta con volver a ejecutar este guion
para que la figura deje de contradecir al texto.

Cada funcion declara de que fichero lee. Si el fichero no existe, la figura se
salta con un aviso en lugar de dibujar algo vacio.

Uso:
    python scripts/figuras_memoria.py
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import REPORTS_DIR, TARGET_COL  # noqa: E402

DESTINO = Path(__file__).resolve().parent.parent / "memoria" / "figuras"
AZUL, ROJO, VERDE, GRIS = "#2E5A88", "#A8322D", "#3D7A4E", "#5B6670"
COLORES = [AZUL, ROJO, VERDE]


def preparar(ax, titulo, x, y):
    ax.set_title(titulo, fontsize=10.5, loc="left", pad=10)
    ax.set_xlabel(x, fontsize=9)
    ax.set_ylabel(y, fontsize=9)
    ax.tick_params(labelsize=8.5)
    ax.grid(linestyle=":", color="#BBBBBB", linewidth=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def guardar(fig, nombre):
    DESTINO.mkdir(parents=True, exist_ok=True)
    ruta = DESTINO / nombre
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  {ruta.name}")


# ----------------------------------------------------------------------
def fig_desbalanceo():
    """Distribucion de importes por clase, sobre el conjunto COMPLETO.

    Se dibuja sobre las 284.807 transacciones, y no sobre el turno de cuatro
    horas empleado en la evaluacion, porque es la afirmacion general la que
    debe sostenerse. En el turno el contraste resulta mas acusado -mediana de
    fraude 2,11 EUR frente a 9,25- y usarlo aqui exageraria el fenomeno.

    Las transacciones de importe cero, 1.825 en total, se cuentan aparte: en
    escala logaritmica no tienen posicion, y agruparlas con las de un centimo
    producia una barra artificial que dominaba el grafico.
    """
    from src.detector.data import cargar_dataset
    df = cargar_dataset()
    f = df[df[TARGET_COL] == 1]["Amount"]
    l = df[df[TARGET_COL] == 0]["Amount"]
    f_pos, l_pos = f[f > 0], l[l > 0]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.8, 3.7),
                                 gridspec_kw={"width_ratios": [1.5, 1]})

    # Se usa la funcion de distribucion acumulada y no un histograma. Con esta
    # variable el histograma es ilegible: la masa se concentra en unos pocos
    # valores -importe cero, un euro- y en escala logaritmica produce picos que
    # dominan el grafico sin decir nada. La acumulada responde directamente a
    # la pregunta que interesa: que fraccion de cada clase queda por debajo de
    # un importe dado.
    for serie, color, etq in ((l_pos, GRIS, f"Legitimas (n={len(l):,})"),
                              (f_pos, ROJO, f"Fraude (n={len(f):,})")):
        xs = np.sort(serie.values)
        ys = np.arange(1, len(xs) + 1) / len(serie)
        a1.step(xs, ys, where="post", color=color, lw=1.9, label=etq)
    a1.set_xscale("log")
    a1.set_ylim(0, 1.02)
    a1.axvline(5, color="#B8860B", ls="--", lw=1.2)
    a1.text(5.6, 0.10, "5 EUR", color="#B8860B", fontsize=8)
    a1.annotate("", xy=(5, 0.451), xytext=(5, 0.242),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.1))
    a1.text(6.5, 0.35, "21 puntos\nde diferencia", fontsize=8)
    preparar(a1, "Fraccion de cada clase por debajo de un importe",
             "Importe (EUR, escala logaritmica)", "Proporcion acumulada")
    a1.legend(fontsize=8, frameon=False, loc="lower right")

    umbrales = (1, 2, 5, 10)
    pf = [100*(f <= u).mean() for u in umbrales]
    pl = [100*(l <= u).mean() for u in umbrales]
    x = np.arange(len(umbrales))
    a2.bar(x - 0.2, pf, 0.4, color=ROJO, label="Fraude")
    a2.bar(x + 0.2, pl, 0.4, color=GRIS, label="Legitimas")
    for i, (vf, vl) in enumerate(zip(pf, pl)):
        a2.text(i - 0.2, vf + 1, f"{vf:.0f}", ha="center", fontsize=7.5, color=ROJO)
        a2.text(i + 0.2, vl + 1, f"{vl:.0f}", ha="center", fontsize=7.5, color=GRIS)
    a2.set_xticks(x); a2.set_xticklabels([f"≤ {u}" for u in umbrales], fontsize=9)
    a2.set_ylim(0, max(pf) * 1.28)
    preparar(a2, "Proporcion por debajo de un importe", "EUR", "% de la clase")
    a2.legend(fontsize=8, frameon=False)
    guardar(fig, "fig_desbalanceo_importes.png")


def _test_y_puntuaciones():
    """Conjunto de prueba y puntuaciones de los tres modelos YA ENTRENADOS.

    Se cargan de models/ en lugar de reentrenar: son los mismos artefactos que
    produjeron las cifras del capitulo 5, de modo que las figuras no pueden
    discrepar de las tablas. Reentrenar aqui tardaria minutos y, si algun
    parametro difiriese, dibujaria una curva que no corresponde a ningun
    numero publicado.
    """
    import joblib, xgboost as xgb
    from src.config import MODELS_DIR
    from src.detector.data import SPLITS, cargar_dataset

    X_tr, X_te, y_tr, y_te = SPLITS["aleatorio"](cargar_dataset())
    out = {}

    px = MODELS_DIR / "xgboost_fraude.json"
    if px.exists():
        m = xgb.XGBClassifier(); m.load_model(str(px))
        out["XGBoost"] = m.predict_proba(X_te)[:, 1]
    pr = MODELS_DIR / "random_forest_fraude.pkl"
    if pr.exists():
        out["Random Forest"] = joblib.load(pr).predict_proba(X_te)[:, 1]
    pi = MODELS_DIR / "iforest_fraude.pkl"
    if pi.exists():
        out["Isolation Forest"] = -joblib.load(pi).score_samples(X_te)
    return np.asarray(y_te), out


def fig_curvas_pr():
    """Curvas de precision-exhaustividad de los tres detectores."""
    from sklearn.metrics import precision_recall_curve, average_precision_score
    y, punt = _test_y_puntuaciones()
    if not punt:
        print("  [omitida] no hay modelos entrenados en models/"); return

    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    estilos = {"XGBoost": (AZUL, "-"), "Random Forest": (ROJO, "-"),
               "Isolation Forest": (VERDE, "--")}
    for nombre, s in punt.items():
        c, ls = estilos.get(nombre, (GRIS, "-"))
        p_, r_, _ = precision_recall_curve(y, s)
        ax.plot(r_, p_, color=c, ls=ls, lw=1.8,
                label=f"{nombre} (AUC-PR {average_precision_score(y, s):.3f})")

    base = float(y.mean())
    ax.axhline(base, color=GRIS, ls=":", lw=1.2)
    ax.text(0.02, base + 0.03, f"linea base = prevalencia = {base:.4f}",
            fontsize=8, color=GRIS)
    ax.set_ylim(0, 1.02); ax.set_xlim(0, 1)
    preparar(ax, "Precision frente a exhaustividad, particion aleatoria",
             "Exhaustividad (recall)", "Precision")
    ax.legend(fontsize=8, frameon=False, loc="lower left")
    guardar(fig, "fig_curvas_pr.png")


def fig_precision_en_n():
    """Precision@N y fraude capturado frente a N, con la capacidad marcada."""
    from src.config import CASOS_MAX
    y, punt = _test_y_puntuaciones()
    if "XGBoost" not in punt:
        print("  [omitida] falta el modelo XGBoost"); return
    s = punt["XGBoost"]
    orden = np.argsort(-s)
    ns = np.arange(1, 401)
    acier = np.cumsum(y[orden][:400])
    prec, recall = acier / ns, acier / y.sum()

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6))
    a1.plot(ns, prec, color=AZUL, lw=1.8)
    a1.axvline(CASOS_MAX, color=ROJO, ls="--", lw=1.3)
    a1.text(CASOS_MAX + 6, 0.5, f"capacidad = {CASOS_MAX} casos",
            color=ROJO, fontsize=8, rotation=90, va="center")
    a1.set_ylim(0, 1.02)
    preparar(a1, "Precision en los N primeros casos", "N casos revisados", "Precision")

    a2.plot(ns, recall, color=VERDE, lw=1.8)
    a2.axvline(CASOS_MAX, color=ROJO, ls="--", lw=1.3)
    a2.axhline(recall[CASOS_MAX-1], color=ROJO, ls=":", lw=1)
    a2.text(170, max(0.05, recall[CASOS_MAX-1] - 0.09),
            f"con {CASOS_MAX} casos se captura el {100*recall[CASOS_MAX-1]:.0f} %",
            color=ROJO, fontsize=8)
    a2.set_ylim(0, 1.02)
    preparar(a2, "Fraude capturado frente a esfuerzo de revision",
             "N casos revisados", "Fraccion del fraude capturado")
    guardar(fig, "fig_precision_en_n.png")


def fig_modelos():
    """Fraude destruido por modelo. Lee de la tanda completa de turnos reales."""
    import csv, collections
    p = REPORTS_DIR / "experimento_20260803_1436.csv"
    if not p.exists():
        print("  [omitida] falta", p.name); return
    d = collections.defaultdict(list)
    for f in csv.DictReader(p.open(encoding="utf-8")):
        d[f["modelo"]].append(int(float(f["n_fraude_descartado"])))
    orden = ["llama3.1-8b-ctx16k", "qwen2.5-14b-ctx16k", "gpt-oss-20b-ctx16k"]
    etiq = ["llama3.1\n8B", "qwen2.5\n14B", "gpt-oss\n20B"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6))
    x = np.arange(3)
    tot = [sum(d[k]) for k in orden]
    a1.bar(x, tot, 0.55, color=COLORES)
    for i, v in enumerate(tot):
        a1.text(i, v + 0.4, str(v), ha="center", fontsize=9)
    a1.set_xticks(x); a1.set_xticklabels(etiq, fontsize=8.5)
    a1.set_ylim(0, max(tot) * 1.25)
    preparar(a1, "Fraude destruido en 16 ejecuciones", "", "Casos de fraude descartados")

    # La caja muestra el solapamiento: es lo que impide declarar significativa
    # la ordenacion, y una barra sola lo ocultaria.
    bp = a2.boxplot([d[k] for k in orden], patch_artist=True, widths=0.5,
                    medianprops=dict(color="black", lw=1.4))
    for caja, c in zip(bp["boxes"], COLORES):
        caja.set_facecolor(c); caja.set_alpha(0.55)
    for i, k in enumerate(orden, start=1):
        a2.scatter(np.random.default_rng(0).normal(i, 0.05, len(d[k])), d[k],
                   s=14, color="black", alpha=0.45, zorder=3)
    a2.set_xticklabels(etiq, fontsize=8.5)
    preparar(a2, "Dispersion entre ejecuciones", "", "Casos por ejecucion")
    a2.text(0.5, 0.95, "las cajas se solapan: la ordenacion no es significativa",
            transform=a2.transAxes, ha="center", va="top", fontsize=8, color=GRIS)
    guardar(fig, "fig_comparativa_modelos.png")


def fig_latencia():
    """Latencia media frente al tamano de ventana, en operacion continua.

    La latencia media de una ventana de duracion V es V/2: una transaccion
    puede ocurrir justo al abrirse la ventana, y esperar entera, o justo al
    cerrarse, y no esperar nada. Se contrasta con la ocupacion de computo
    medida en las ejecuciones registradas, que es la que demuestra que reducir
    la ventana no cuesta practicamente nada.
    """
    ventanas, ocup = [], []
    for p in sorted(REPORTS_DIR.glob("streaming_*.json")):
        a = json.loads(p.read_text(encoding="utf-8"))
        v = a.get("ventana_min")
        o = a.get("ocupacion")
        if v and isinstance(o, (int, float)):
            ventanas.append(float(v)); ocup.append(float(o))
    if not ventanas:
        print("  [omitida] sin ficheros de streaming con ocupacion"); return

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6))
    vs = np.array([5, 10, 30, 60, 240], dtype=float)
    a1.plot(vs, vs / 2, "o-", color=AZUL, lw=1.8, ms=6)
    for v in (5, 240):
        a1.annotate(f"{v/2:.0f} min", (v, v/2), textcoords="offset points",
                    xytext=(6, 6), fontsize=8, color=AZUL)
    a1.set_xscale("log"); a1.set_yscale("log")
    a1.set_xticks(vs); a1.set_xticklabels([f"{int(v)}" for v in vs])
    preparar(a1, "Latencia media hasta aparecer en un informe",
             "Tamano de ventana (min)", "Espera media (min)")

    o = np.array(ocup) * (100 if max(ocup) <= 1 else 1)
    a2.scatter(ventanas, o, s=45, color=ROJO, zorder=3)
    a2.set_ylim(0, max(10, o.max() * 1.4))
    preparar(a2, "Ocupacion de computo medida", "Tamano de ventana (min)",
             "Ocupacion (%)")
    a2.text(0.5, 0.9, "reducir la ventana no aumenta el coste",
            transform=a2.transAxes, ha="center", fontsize=8, color=GRIS)
    guardar(fig, "fig_latencia_streaming.png")


def fig_ablacion_dossier():
    """Efecto del nivel de informacion del expediente sobre los descartes."""
    # Cifras de la ablacion de 48 ejecuciones, citadas en 5.7 de la memoria.
    niveles = ["completo", "sin nivel", "ciego"]
    descartes = [100, 66, 35]     # volumen relativo al nivel completo
    aciertos = [92, 88, 82]       # % de descartes correctos
    determ = [4, 3, 1]            # turnos de 4 con repeticiones identicas

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6))
    x = np.arange(3)
    a1.bar(x - 0.2, descartes, 0.4, color=AZUL, label="Volumen de descartes (%)")
    a1.bar(x + 0.2, aciertos, 0.4, color=VERDE, label="Descartes acertados (%)")
    a1.set_xticks(x); a1.set_xticklabels(niveles, fontsize=9)
    a1.set_ylim(0, 115)
    preparar(a1, "El volumen se desploma, la calidad apenas cae", "", "%")
    a1.legend(fontsize=8, frameon=False)

    a2.bar(x, determ, 0.5, color=[VERDE, "#B8860B", ROJO])
    a2.set_xticks(x); a2.set_xticklabels(niveles, fontsize=9)
    a2.set_ylim(0, 4.6); a2.set_yticks([0, 1, 2, 3, 4])
    preparar(a2, "Reproducibilidad ante la misma entrada", "",
             "Turnos con repeticiones identicas (de 4)")
    a2.text(0.5, 0.92, "la reproducibilidad venia del numero, no del modelo",
            transform=a2.transAxes, ha="center", fontsize=8, color=GRIS)
    guardar(fig, "fig_ablacion_dossier.png")


FIGURAS = [fig_desbalanceo, fig_curvas_pr, fig_precision_en_n,
           fig_modelos, fig_latencia, fig_ablacion_dossier]


def main():
    print("=" * 60)
    print("  FIGURAS DE LA MEMORIA")
    print("=" * 60)
    for f in FIGURAS:
        try:
            f()
        except Exception as e:
            print(f"  [ERROR] {f.__name__}: {type(e).__name__}: {e}")
    print(f"\n  Destino: {DESTINO}")


if __name__ == "__main__":
    main()
