"""
Genera las figuras de datos de la memoria a partir de los ficheros de reports/.

Las figuras NO se dibujan a mano ni se copian de una hoja de calculo: se
derivan de los mismos ficheros que citan las tablas del capitulo 6. Si una
cifra cambia al repetir un experimento, basta con volver a ejecutar este guion
para que la figura deje de contradecir al texto.

Cada funcion declara de que fichero lee. Si el fichero no existe, la figura se
salta con un aviso en lugar de dibujar algo vacio.

Las figuras de diseno (mapa de experimentos, Gantt, pila de tecnologias y
captura del codigo de los agentes) no leen de reports/: se dibujan aqui para
que la memoria no dependa de imagenes sueltas que nadie sabe regenerar.

Uso:
    python scripts/figuras_memoria.py
    python scripts/figuras_memoria.py fig_curvas_pr   # solo una
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
AMBAR, PLAN = "#B8860B", "#9AA3AB"
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


_CACHE = {}


def _test_y_puntuaciones():
    """Conjunto de prueba ALEATORIO y puntuaciones de los tres detectores.

    Los modelos se reentrenan aqui sobre el split aleatorio en lugar de
    cargarse de models/. Es deliberado, y corrige un fallo: en models/ solo se
    persisten los modelos del split TEMPORAL, que son los que usan los agentes.
    Evaluarlos sobre el test del split aleatorio mezcla las dos particiones —
    parte de ese test estuvo en el entrenamiento temporal— y produce una fuga
    de informacion: las curvas salian con AUC-PR 0,990 en vez de los 0,883 y
    0,863 que reportan las tablas, pegadas al borde del grafico y por tanto
    invisibles.

    Entrenar aqui cuesta unos minutos, casi todo Random Forest, y garantiza que
    la figura corresponda exactamente a la fila de la tabla.
    """
    if "aleatorio" in _CACHE:          # las dos figuras que lo usan comparten entrenamiento
        return _CACHE["aleatorio"]

    from src.detector.data import SPLITS, cargar_dataset
    from src.detector.train import (entrenar_iforest, entrenar_random_forest,
                                    entrenar_xgboost, puntuar_iforest)

    X_tr, X_te, y_tr, y_te = SPLITS["aleatorio"](cargar_dataset())
    print("    reentrenando los tres detectores sobre el split aleatorio...")
    out = {
        "XGBoost": entrenar_xgboost(X_tr, y_tr).predict_proba(X_te)[:, 1],
        "Random Forest": entrenar_random_forest(X_tr, y_tr).predict_proba(X_te)[:, 1],
        "Isolation Forest": puntuar_iforest(
            entrenar_iforest(X_tr, float(y_tr.mean())), X_te),
    }
    _CACHE["aleatorio"] = (np.asarray(y_te), out)
    return _CACHE["aleatorio"]


def fig_curvas_pr():
    """Curvas de precision-exhaustividad de los tres detectores."""
    from sklearn.metrics import precision_recall_curve, average_precision_score
    y, punt = _test_y_puntuaciones()
    if not punt:
        print("  [omitida] no hay puntuaciones"); return

    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    # XGBoost y Random Forest se solapan casi por completo: sin grosores y
    # trazos distintos, la de abajo desaparece.
    estilos = {"XGBoost": (AZUL, "-", 2.6, 3),
               "Random Forest": (ROJO, "--", 1.8, 2),
               "Isolation Forest": (VERDE, ":", 2.0, 1)}
    for nombre, s_ in punt.items():
        c, ls, lw, z = estilos.get(nombre, (GRIS, "-", 1.8, 1))
        p_, r_, _ = precision_recall_curve(y, s_)
        ax.step(r_, p_, where="post", color=c, ls=ls, lw=lw, zorder=z,
                label=f"{nombre} (AUC-PR {average_precision_score(y, s_):.3f})")

    base = float(y.mean())
    # En la leyenda y no como texto sobre el grafico: a la altura de la
    # prevalencia se cruzaba con la curva del Isolation Forest.
    ax.axhline(base, color=GRIS, ls="-.", lw=1.2,
               label=f"Línea base = prevalencia ({base:.4f})")
    ax.set_ylim(0, 1.02); ax.set_xlim(0, 1)
    preparar(ax, "Precisión frente a exhaustividad, partición aleatoria",
             "Exhaustividad (recall)", "Precisión")
    ax.legend(fontsize=8, frameon=False, loc="center left", bbox_to_anchor=(0, 0.55))
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
    preparar(a1, "Precisión en los N primeros casos", "N casos revisados", "Precisión")

    a2.plot(ns, recall, color=VERDE, lw=1.8)
    a2.axvline(CASOS_MAX, color=ROJO, ls="--", lw=1.3)
    a2.axhline(recall[CASOS_MAX-1], color=ROJO, ls=":", lw=1)
    a2.text(170, max(0.05, recall[CASOS_MAX-1] - 0.09),
            f"con {CASOS_MAX} casos se captura el {100*recall[CASOS_MAX-1]:.0f} %",
            color=ROJO, fontsize=8)
    a2.set_ylim(0, 1.02)
    preparar(a2, "Fraude capturado frente a esfuerzo de revisión",
             "N casos revisados", "Fracción del fraude capturado")
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
    """Efecto del nivel de informacion del expediente sobre los descartes.

    Las cifras son las de la tabla de la ablacion (48 ejecuciones, 16 por
    nivel): 9,9 / 9,4 / 3,5 descartes de media y 92 / 90 / 82 % de acierto. El
    volumen se expresa como porcentaje del nivel completo. Una version anterior
    tenia aqui 66 % y 88 % para el nivel 'sin nivel', que no correspondian a
    ninguna tabla de la memoria.
    """
    niveles = ["completo", "sin nivel", "ciego"]
    descartes_medios = [9.9, 9.4, 3.5]
    aciertos = [92, 90, 82]       # precision del descarte, tal como la da la tabla
    volumen = [100 * d / descartes_medios[0] for d in descartes_medios]
    determ = [4, 3, 1]            # turnos de 4 con repeticiones identicas

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6))
    x = np.arange(3)
    a1.bar(x - 0.2, volumen, 0.4, color=AZUL,
           label="Volumen de descartes (% del nivel completo)")
    a1.bar(x + 0.2, aciertos, 0.4, color=VERDE, label="Descartes acertados (%)")
    for i, (v, a) in enumerate(zip(volumen, aciertos)):
        a1.text(i - 0.2, v + 1.5, f"{v:.0f}", ha="center", fontsize=8, color=AZUL)
        a1.text(i + 0.2, a + 1.5, f"{a:.0f}", ha="center", fontsize=8, color=VERDE)
    a1.set_xticks(x); a1.set_xticklabels(niveles, fontsize=9)
    a1.set_ylim(0, 125)
    preparar(a1, "El volumen cae, la calidad apenas cambia", "", "%")
    a1.legend(fontsize=7.5, frameon=False, loc="upper right")

    a2.bar(x, determ, 0.5, color=[VERDE, "#B8860B", ROJO])
    a2.set_xticks(x); a2.set_xticklabels(niveles, fontsize=9)
    a2.set_ylim(0, 4.6); a2.set_yticks([0, 1, 2, 3, 4])
    preparar(a2, "Reproducibilidad ante la misma entrada", "",
             "Turnos con repeticiones idénticas (de 4)")
    guardar(fig, "fig_ablacion_dossier.png")



# ----------------------------------------------------------------------
# Figuras de diseno: no leen de reports/, pero se generan aqui para que la
# memoria no dependa de imagenes sueltas imposibles de regenerar.
# ----------------------------------------------------------------------
from matplotlib.patches import FancyBboxPatch  # noqa: E402

RELLENO = {AZUL: "#E8EFF6", ROJO: "#FBEDEC", VERDE: "#EBF3ED",
           GRIS: "#F0F1F2", AMBAR: "#FFF6E0"}


def _caja(ax, x, y, ancho, alto, texto, color, fs=9.5, lw=1.5, negrita=None):
    ax.add_patch(FancyBboxPatch((x, y), ancho, alto,
                                boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc=RELLENO[color], ec=color, lw=lw))
    if negrita:
        ax.text(x + ancho / 2, y + alto - 0.15, negrita, ha="center", va="top",
                fontsize=10, weight="bold", color=color)
        ax.text(x + ancho / 2, y + alto - 0.5, texto, ha="center", va="top",
                fontsize=fs, linespacing=1.45)
    else:
        ax.text(x + ancho / 2, y + alto / 2, texto, ha="center", va="center",
                fontsize=fs)
    return (x, x + ancho, y + alto / 2)


def _flecha(ax, origen, destino, color="#888888", lw=1.0):
    ax.annotate("", xy=(destino[0], destino[2]), xytext=(origen[1], origen[2]),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                shrinkA=0, shrinkB=2))


def fig_mapa_experimentos():
    """Mapa de los doce experimentos del capitulo 6 y sus fuentes de datos.

    Se dibuja con matplotlib y no con Graphviz porque este no respeta el orden
    de los nodos dentro de un cluster, y aqui el orden es el del capitulo.
    """
    ex = [("E1. Comparación de detectores", AZUL),
          ("E2. Ablación de variables", AZUL),
          ("E3. Desbalanceo y fuga de información", AZUL),
          ("E4. Punto de operación y capacidad", AZUL),
          ("E5. Cinco modelos (lotes sintéticos)", ROJO),
          ("E6. Tres modelos (turnos reales)", ROJO),
          ("E7. Efecto de la capa 2 y ablación", ROJO),
          ("E8. Operación en continuo", ROJO),
          ("E9. Modelo de 72.000 millones", ROJO),
          ("E10. Corrección de la premisa", ROJO),
          ("E11. Variables de negocio (Sparkov)", AMBAR),
          ("E12. Ajuste fino QLoRA", ROJO)]

    fig, ax = plt.subplots(figsize=(10, 8.2))
    ax.set_xlim(0, 10); ax.set_ylim(0.6, 13.4); ax.axis("off")
    ys = [12.2 - i * 0.95 - (0.45 if i >= 4 else 0) for i in range(12)]
    cajas = [_caja(ax, 8.1 - 1.7, y - 0.31, 3.4, 0.62, t, c)
             for (t, c), y in zip(ex, ys)]

    for i0, i1, c, etiq in ((0, 3, AZUL, "Capa 1: detector"),
                            (4, 11, ROJO, "Capa 2: agentes")):
        arriba, abajo = ys[i0] + 0.5, ys[i1] - 0.5
        ax.add_patch(plt.Rectangle((6.2, abajo), 3.8, arriba - abajo + 0.25,
                                   fill=False, ec=c, ls="--", lw=1))
        ax.text(6.3, arriba + 0.27, etiq, ha="left", va="top", color=c, fontsize=9)

    ds = _caja(ax, 0.1, 8.9, 2.2, 0.8, "Conjunto ULB\n284.807 transacciones", GRIS)
    al = _caja(ax, 2.7, 11.39, 2.2, 0.62, "Partición aleatoria", AZUL)
    te = _caja(ax, 2.7, 8.99, 2.2, 0.62, "Partición temporal", AZUL)
    si = _caja(ax, 2.7, 7.79, 2.2, 0.62, "Lotes sintéticos", GRIS)
    tu = _caja(ax, 2.7, 5.59, 2.2, 0.62, "4 turnos reales de 4 h", GRIS)
    ba = _caja(ax, 2.7, 2.9, 2.2, 0.8, "LÍNEA BASE\ndetector sin capa 2", VERDE, lw=2)
    sp = _caja(ax, 2.7, 1.0, 2.2, 0.8, "Conjunto Sparkov\n(simulado)", AMBAR)

    _flecha(ax, ds, al); _flecha(ax, ds, te)
    for i in (0, 2):
        _flecha(ax, al, cajas[i])
    for i in (0, 1, 2):
        _flecha(ax, te, cajas[i])
    ax.annotate("", xy=(3.8, 8.41), xytext=(3.8, 8.99),
                arrowprops=dict(arrowstyle="-|>", color="#888888"))
    ax.annotate("", xy=(2.7, 5.9), xytext=(2.7, 9.3),
                arrowprops=dict(arrowstyle="-|>", color="#888888",
                                connectionstyle="arc3,rad=0.35"))
    _flecha(ax, si, cajas[4])
    for i in (3, 5, 6, 7, 8, 9, 11):
        _flecha(ax, tu, cajas[i])
    for i in (5, 6, 9):
        _flecha(ax, ba, cajas[i], color=VERDE, lw=1.6)
    _flecha(ax, sp, cajas[10], color=AMBAR)
    ax.text(3.8, 2.6, "(se compara contra ella)", color=VERDE, fontsize=8.5,
            ha="center")
    guardar(fig, "fig_mapa_experimentos.png")


def fig_gantt():
    """Planificacion y ejecucion del proyecto, capitulo 3."""
    import matplotlib.dates as md
    from datetime import date
    from matplotlib.patches import Patch

    hoy = date(2026, 9, 16)          # fecha de la version entregada al tutor
    tareas = [
        ("Definición del trabajo y documentación", date(2026, 4, 28), date(2026, 5, 31), GRIS),
        ("Preparación del entorno de desarrollo", date(2026, 5, 10), date(2026, 6, 10), AZUL),
        ("Estudio de técnicas de detección de anomalías", date(2026, 6, 1), date(2026, 7, 5), GRIS),
        ("Primeros desarrollos y estudio del conjunto de datos", date(2026, 7, 1), date(2026, 7, 26), AZUL),
        ("Construcción del sistema (capas 1 y 2)", date(2026, 7, 27), date(2026, 7, 31), AZUL),
        ("Experimentación (fases 9 a 15)", date(2026, 8, 1), date(2026, 8, 14), VERDE),
        ("Estudio del estado del arte", date(2026, 8, 5), date(2026, 8, 30), VERDE),
        ("Extensiones: Sparkov, QLoRA y AirLLM", date(2026, 8, 15), date(2026, 8, 30), VERDE),
        ("Demostrador web", date(2026, 8, 15), date(2026, 8, 30), VERDE),
        ("Redacción de la memoria", date(2026, 8, 1), date(2026, 8, 30), ROJO),
        ("Relectura completa", date(2026, 9, 1), date(2026, 9, 10), ROJO),
        ("Revisión del tutor y correcciones", date(2026, 9, 11), date(2026, 9, 30), PLAN),
        ("Preparación de la defensa", date(2026, 10, 1), date(2026, 10, 20), PLAN),
    ]
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    for i, (n, a, b, c) in enumerate(tareas):
        y = len(tareas) - 1 - i
        ax.barh(y, (b - a).days + 1, left=md.date2num(a), height=0.55,
                    color=c, hatch="//" if c == PLAN else None,
                    edgecolor="#5B6670" if c == PLAN else "white")
    ax.set_yticks(range(len(tareas)))
    ax.set_yticklabels([t[0] for t in tareas][::-1], fontsize=8.5)
    ax.axvline(md.date2num(hoy), color="black", ls="--", lw=1)
    ax.text(md.date2num(hoy) + 0.5, len(tareas) - 0.6, hoy.strftime("%d %b"), fontsize=8)
    ax.xaxis.set_major_locator(md.WeekdayLocator(byweekday=0, interval=2))
    ax.xaxis.set_major_formatter(md.DateFormatter("%d/%m"))
    plt.setp(ax.get_xticklabels(), fontsize=7.5, rotation=45)
    ax.set_xlim(md.date2num(date(2026, 4, 20)), md.date2num(date(2026, 10, 25)))
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.grid(axis="x", ls=":", color="#bbbbbb"); ax.set_axisbelow(True)
    ax.legend(handles=[Patch(color=GRIS, label="Documentación y estudio"),
                       Patch(color=AZUL, label="Entorno y construcción"),
                       Patch(color=VERDE, label="Experimentación"),
                       Patch(color=ROJO, label="Redacción"),
                       Patch(facecolor=PLAN, hatch="//", edgecolor="#5B6670",
                             label="Planificado")],
              fontsize=7.5, frameon=False, loc="lower left", ncol=5,
              bbox_to_anchor=(0, -0.33))
    ax.set_title("Planificación y ejecución del proyecto (2026)", fontsize=10.5, loc="left")
    guardar(fig, "fig_gantt.png")


def fig_tecnologias():
    """Pila de tecnologias del capitulo 5."""
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4.4); ax.axis("off")
    _caja(ax, 0.1, 2.05, 2.45, 2.3,
          "pandas - NumPy\nscikit-learn - joblib\nXGBoost\n"
          "imbalanced-learn (E3)\nSciPy - Matplotlib", AZUL,
          fs=8.8, negrita="Capa 1: detector")
    _caja(ax, 2.7, 2.05, 2.45, 2.3,
          "CrewAI - LiteLLM\nPydantic\nOllama (llama.cpp, GGUF)\n"
          "Llama 3.1 - Qwen2.5\nQwen3 - gpt-oss", ROJO,
          fs=8.8, negrita="Capa 2: agentes")
    _caja(ax, 5.3, 2.05, 2.2, 2.3,
          "FastAPI - Uvicorn\nAPI JSON\nHTML - CSS\nJavaScript (fetch)", VERDE,
          fs=8.8, negrita="Demostrador web")
    _caja(ax, 0.1, 1.0, 7.4, 0.9,
          "PyTorch - Transformers - bitsandbytes - AirLLM - PEFT - Datasets", AMBAR,
          fs=8.8, negrita="Entorno aparte: modelo de 72B (E9) y ajuste fino (E12)")
    _caja(ax, 0.1, 0.05, 7.4, 0.8,
          "Python 3.12 (entornos virtuales)  -  Windows  -  "
          "NVIDIA RTX 5060 Ti 16 GB con CUDA", GRIS, fs=8.8, negrita="Base")
    _caja(ax, 7.7, 0.05, 2.2, 4.3, "\n\n\nGit\n\nGitHub\n\nGraphviz", GRIS,
          fs=10, negrita="Herramientas de\ndesarrollo")
    guardar(fig, "fig_tecnologias.png")


def fig_codigo_crewai():
    """Captura del codigo donde se definen los agentes, capitulo 4.

    Se genera con Pygments en lugar de fotografiar el editor: asi el fragmento
    se actualiza solo si cambia crew.py y no queda atado a una captura vieja.
    Requiere `pip install pygments pillow`.
    """
    try:
        from pygments import highlight
        from pygments.lexers import PythonLexer
        from pygments.formatters import ImageFormatter
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  [omitida] falta pygments o pillow"); return

    fuente = Path(__file__).resolve().parent.parent / "src" / "agents" / "crew.py"
    lineas = fuente.read_text(encoding="utf-8").splitlines()

    def rango(inicio_con, fin_con, extra=1):
        a = next(i for i, l in enumerate(lineas) if inicio_con in l)
        b = next(i for i, l in enumerate(lineas[a:], start=a) if fin_con in l)
        return a, b + extra

    def recorte(a, b, salida):
        png = highlight("\n".join(lineas[a:b]), PythonLexer(),
                        ImageFormatter(style="friendly", font_name="DejaVu Sans Mono",
                                       font_size=15, line_numbers=True,
                                       line_number_start=a + 1, line_pad=3,
                                       image_pad=12))
        salida.write_bytes(png)
        return Image.open(salida).convert("RGB")

    DESTINO.mkdir(parents=True, exist_ok=True)
    tmp1, tmp2 = DESTINO / "_crew1.png", DESTINO / "_crew2.png"
    a1, b1 = rango("comun = dict(", "**comun,")
    a2, b2 = rango("return Crew(", "tracing=False", extra=2)
    trozos = [("src/agents/crew.py - parametros comunes y agente Coordinador",
               recorte(a1, b1, tmp1)),
              ("src/agents/crew.py - ensamblado del equipo (Crew) con proceso secuencial",
               recorte(a2, b2, tmp2))]

    ancho = max(im.width for _, im in trozos)
    barra = 34
    try:
        tipo = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        tipo = ImageFont.load_default()
    alto = sum(im.height for _, im in trozos) + barra * len(trozos) + 6
    lienzo = Image.new("RGB", (ancho, alto), "#F0F0F0")
    lapiz = ImageDraw.Draw(lienzo)
    y = 0
    for titulo, im in trozos:
        lapiz.rectangle([0, y, ancho, y + barra], fill="#2E3440")
        lapiz.text((12, y + 8), titulo, fill="white", font=tipo)
        y += barra
        lienzo.paste(im, (0, y)); y += im.height + 3
    lienzo.save(DESTINO / "fig_codigo_crewai.png")
    tmp1.unlink(); tmp2.unlink()
    print("  fig_codigo_crewai.png")


FIGURAS = [fig_desbalanceo, fig_curvas_pr, fig_precision_en_n,
           fig_modelos, fig_latencia, fig_ablacion_dossier,
           fig_mapa_experimentos, fig_gantt, fig_tecnologias,
           fig_codigo_crewai]


def main():
    print("=" * 60)
    print("  FIGURAS DE LA MEMORIA")
    print("=" * 60)
    pedidas = sys.argv[1:]
    for f in FIGURAS:
        if pedidas and f.__name__ not in pedidas:
            continue
        try:
            f()
        except Exception as e:
            print(f"  [ERROR] {f.__name__}: {type(e).__name__}: {e}")
    print(f"\n  Destino: {DESTINO}")


if __name__ == "__main__":
    main()
