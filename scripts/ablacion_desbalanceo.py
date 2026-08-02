"""
Ablacion del tratamiento del desbalanceo - capa 1.

Responde a dos preguntas distintas que conviene no mezclar:

  1. ¿Que estrategia rinde mejor sobre estos datos?
     Compara no hacer nada, ponderar el gradiente y aplicar SMOTE
     correctamente, es decir, DESPUES de partir en entrenamiento y prueba.

  2. ¿Cuanto inflan los resultados si SMOTE se aplica MAL?
     Reproduce deliberadamente el error metodologico documentado en la
     literatura -aplicar el remuestreo ANTES de partir- y mide la diferencia.

La segunda es la interesante. La literatura afirma que ese error produce
metricas infladas artificialmente; este guion lo comprueba sobre los datos
propios del trabajo, que es bastante mas defendible que citarlo.

## Por que el error infla

SMOTE crea ejemplos sinteticos interpolando entre vecinos de la clase
minoritaria. Si se aplica antes de partir, un ejemplo sintetico puede haberse
generado interpolando entre una observacion que acabara en entrenamiento y
otra que acabara en prueba. El modelo entrena entonces sobre informacion
derivada del conjunto con el que sera evaluado.

Ademas el conjunto de prueba queda contaminado con ejemplos sinteticos, que
son por construccion mas faciles de clasificar que los reales: viven en el
interior de la nube de puntos de su clase, no en la frontera.

## Como se mide la inflacion, y por que no se puede medir de otra forma

Una primera version de este guion evaluaba el modelo con fuga sobre la
particion de prueba original, suponiendo que eso daria su rendimiento "real".
Es incorrecto: ese modelo entreno sobre ejemplos derivados del conjunto
COMPLETO, incluido el periodo que la particion temporal reserva para prueba.
No existe ninguna particion limpia sobre la que evaluarlo.

Esa es precisamente la conclusion, y es mas fuerte que una inflacion
cuantificada: **una vez aplicado el remuestreo antes de partir, el modelo ya
no puede evaluarse honestamente en ningun conjunto**. La metrica no queda algo
inflada; deja de significar nada.

Por tanto la inflacion se mide como la diferencia entre lo que reportaria el
trabajo erroneo y el mejor resultado obtenido por un procedimiento sin fuga.

Requiere: pip install imbalanced-learn

Uso:
    python scripts/ablacion_desbalanceo.py
    python scripts/ablacion_desbalanceo.py --split aleatorio
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import FEATURE_COLS, RANDOM_STATE, REPORTS_DIR, TARGET_COL  # noqa: E402
from src.detector.data import SPLITS, cargar_dataset  # noqa: E402

TOP_N = (20, 50, 100, 200)


def parsear_args():
    p = argparse.ArgumentParser(description="Ablacion del tratamiento del desbalanceo")
    p.add_argument("--split", choices=list(SPLITS), default="temporal")
    p.add_argument("--test-size", type=float, default=0.2)
    return p.parse_args()


def entrenar(X, y, spw=None):
    """XGBoost con la misma configuracion que el detector de produccion.

    Solo cambia `scale_pos_weight`: es la variable de la ablacion. Todo lo
    demas se mantiene fijo para que la comparacion sea limpia.
    """
    modelo = xgb.XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=spw if spw else 1,
        eval_metric="aucpr", tree_method="hist",
        n_jobs=-1, random_state=RANDOM_STATE,
    )
    modelo.fit(X, y)
    return modelo


def evaluar(modelo, X, y, etiqueta):
    s = modelo.predict_proba(X)[:, 1]
    y = np.asarray(y)
    return {
        "estrategia": etiqueta,
        "auc_pr": float(average_precision_score(y, s)),
        "roc_auc": float(roc_auc_score(y, s)),
        "p_at_n": {n: float(y[np.argsort(-s)[:n]].mean()) for n in TOP_N},
        "n_test": int(len(y)),
        "fraudes_test": int(y.sum()),
    }


def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)

    try:
        from imblearn.over_sampling import SMOTE
    except ImportError:
        print("\n  Falta imbalanced-learn. Instalalo con:")
        print("      pip install imbalanced-learn\n")
        sys.exit(1)

    print("=" * 70)
    print("  ABLACION DEL TRATAMIENTO DEL DESBALANCEO")
    print("=" * 70)
    print(f"  Particion: {args.split}")

    df = cargar_dataset()
    X_tr, X_te, y_tr, y_te = SPLITS[args.split](df)
    n_neg, n_pos = int((y_tr == 0).sum()), int((y_tr == 1).sum())
    spw = n_neg / n_pos

    print(f"  Entrenamiento: {len(X_tr):,} ({n_pos} fraudes)")
    print(f"  Prueba       : {len(X_te):,} ({int(np.asarray(y_te).sum())} fraudes)")
    print(f"  scale_pos_weight = {spw:.1f}\n")

    resultados = []

    # --- 1. Sin tratamiento -------------------------------------------
    print("  [1/4] Sin tratamiento del desbalanceo...")
    t0 = time.perf_counter()
    m = entrenar(X_tr, y_tr)
    r = evaluar(m, X_te, y_te, "Sin tratamiento")
    r["correcto"] = True
    resultados.append(r)
    print(f"        AUC-PR {r['auc_pr']:.4f}  ({time.perf_counter()-t0:.0f}s)")

    # --- 2. Ponderacion del gradiente (la del trabajo) ------------------
    print("  [2/4] Ponderacion del gradiente (configuracion del trabajo)...")
    t0 = time.perf_counter()
    m = entrenar(X_tr, y_tr, spw)
    r = evaluar(m, X_te, y_te, "Ponderacion del gradiente")
    r["correcto"] = True
    resultados.append(r)
    print(f"        AUC-PR {r['auc_pr']:.4f}  ({time.perf_counter()-t0:.0f}s)")

    # --- 3. SMOTE aplicado BIEN: despues de partir ----------------------
    print("  [3/4] SMOTE despues de partir (aplicacion correcta)...")
    t0 = time.perf_counter()
    X_res, y_res = SMOTE(random_state=RANDOM_STATE).fit_resample(X_tr, y_tr)
    m = entrenar(X_res, y_res)
    r = evaluar(m, X_te, y_te, "SMOTE tras la division")
    r["correcto"] = True
    r["n_train_tras_smote"] = int(len(X_res))
    resultados.append(r)
    print(f"        entrenamiento: {len(X_tr):,} -> {len(X_res):,} filas")
    print(f"        AUC-PR {r['auc_pr']:.4f}  ({time.perf_counter()-t0:.0f}s)")

    # --- 4. SMOTE aplicado MAL: antes de partir -------------------------
    # Se reproduce el error a proposito. El remuestreo se aplica al conjunto
    # COMPLETO y solo despues se divide, de modo que ejemplos sinteticos
    # derivados de observaciones de prueba acaban en el entrenamiento y
    # viceversa.
    print("  [4/4] SMOTE antes de partir (error metodologico, deliberado)...")
    t0 = time.perf_counter()
    X_todo = df[FEATURE_COLS]
    y_todo = df[TARGET_COL]
    X_mal, y_mal = SMOTE(random_state=RANDOM_STATE).fit_resample(X_todo, y_todo)

    # Division posterior al remuestreo, tal como la haria el trabajo erroneo
    from sklearn.model_selection import train_test_split
    Xm_tr, Xm_te, ym_tr, ym_te = train_test_split(
        X_mal, y_mal, test_size=args.test_size,
        random_state=RANDOM_STATE, stratify=y_mal)

    m = entrenar(Xm_tr, ym_tr)

    # (a) Lo que REPORTARIA ese trabajo: sobre el test contaminado
    r_rep = evaluar(m, Xm_te, ym_te, "SMOTE antes de partir (reportado)")
    r_rep["correcto"] = False
    resultados.append(r_rep)

    # (b) El mismo modelo sobre la particion original. NO es una evaluacion
    # limpia -el remuestreo previo contamino tambien ese conjunto- y se
    # registra unicamente para dejar constancia de que tampoco ahi baja: es
    # la prueba de que no queda ninguna particion utilizable.
    r_ctrl = evaluar(m, X_te, y_te,
                     "SMOTE antes de partir (particion original, tambien contaminada)")
    r_ctrl["correcto"] = False
    resultados.append(r_ctrl)

    print(f"        reportado sobre su propio test : AUC-PR {r_rep['auc_pr']:.4f}")
    print(f"        sobre la particion original    : AUC-PR {r_ctrl['auc_pr']:.4f}")
    print(f"        ({time.perf_counter()-t0:.0f}s)")

    # --- Tabla ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("  RESULTADOS")
    print("=" * 70 + "\n")
    print(f"  {'Estrategia':<38}{'AUC-PR':>9}{'ROC-AUC':>10}{'P@50':>8}")
    print("  " + "-" * 65)
    for r in resultados:
        marca = " " if r["correcto"] else "!"
        print(f"  {marca}{r['estrategia']:<37}{r['auc_pr']:>9.4f}"
              f"{r['roc_auc']:>10.4f}{r['p_at_n'][50]:>8.3f}")
    print("  " + "-" * 65)
    print("  ! = procedimiento con fuga de informacion\n")

    mejor = max((r for r in resultados if r["correcto"]), key=lambda r: r["auc_pr"])
    inflacion = r_rep["auc_pr"] - mejor["auc_pr"]
    rel = inflacion / mejor["auc_pr"] if mejor["auc_pr"] else 0

    print(f"  Mejor procedimiento SIN fuga : {mejor['estrategia']}")
    print(f"                                 AUC-PR {mejor['auc_pr']:.4f}")
    print(f"  Reportado CON fuga           : AUC-PR {r_rep['auc_pr']:.4f}")
    print(f"  INFLACION                    : {inflacion:+.4f}  ({rel:+.1%})\n")
    print("  El modelo con fuga NO puede evaluarse honestamente en ninguna")
    print("  particion: el remuestreo previo contamino todas. Su metrica no")
    print("  esta algo inflada, ha dejado de significar nada.")

    destino = REPORTS_DIR / f"ablacion_desbalanceo_{args.split}.json"
    destino.write_text(json.dumps({
        "split": args.split,
        "resultados": resultados,
        "inflacion_auc_pr": float(inflacion),
        "inflacion_relativa": float(rel),
        "mejor_sin_fuga": mejor["estrategia"],
        "auc_pr_mejor_sin_fuga": float(mejor["auc_pr"]),
        "auc_pr_reportado_con_fuga": float(r_rep["auc_pr"]),
        "nota": ("La inflacion se mide contra el mejor procedimiento sin fuga. "
                 "El modelo con fuga no admite evaluacion honesta en ninguna "
                 "particion, porque el remuestreo previo las contamino todas."),
    }, indent=2), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")


if __name__ == "__main__":
    main()
