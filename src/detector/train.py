"""
Entrenamiento del detector de fraude - Fase 2.

Capa 1 del sistema: el instrumento que puntua el riesgo. Los agentes LLM de la
Fase 3 lo consultaran como herramienta, pero no participan aqui.

Se entrenan dos modelos complementarios sobre dos particiones distintas:

  XGBoost (supervisado)          -> aprovecha las 492 etiquetas de fraude.
                                    Es el detector principal.
  Isolation Forest (no superv.)  -> no mira las etiquetas en absoluto; detecta
                                    lo que se desvia de lo normal. Aporta el
                                    angulo de anomalia y da cobertura frente a
                                    fraude nuevo, sin precedentes etiquetados.

Uso:
    python -m src.detector.train
"""

import json
import time

import joblib
import numpy as np
import xgboost as xgb
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import FEATURE_COLS, MODELS_DIR, RANDOM_STATE, REPORTS_DIR
from src.detector.data import SPLITS, cargar_dataset, resumen_split
from src.detector.metrics import evaluar, imprimir, tabla_comparativa


def entrenar_xgboost(X_train, y_train):
    """XGBoost con ponderacion de la clase minoritaria.

    scale_pos_weight = n_negativos / n_positivos (~578). Multiplica el peso del
    gradiente de los fraudes, de modo que el modelo paga por ignorarlos. Es la
    alternativa a remuestrear: no inventa datos sinteticos ni descarta
    informacion, y no puede provocar fugas entre train y test.
    """
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    spw = n_neg / n_pos
    print(f"    scale_pos_weight = {n_neg:,}/{n_pos} = {spw:.1f}")

    modelo = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=spw,
        eval_metric="aucpr",     # optimizar AUC-PR, no exactitud
        tree_method="hist",      # CPU: con 284k filas sobra, tarda segundos
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    t0 = time.perf_counter()
    modelo.fit(X_train, y_train)
    print(f"    entrenado en {time.perf_counter() - t0:.1f}s")
    return modelo


def entrenar_iforest(X_train, contaminacion):
    """Isolation Forest sobre datos estandarizados.

    Reutiliza el patron Pipeline(escalado -> IForest) del TFG anterior. A
    diferencia de XGBoost, NO ve las etiquetas: se entrena solo con X.
    """
    pipe = Pipeline([
        ("escalado", StandardScaler()),
        ("iforest", IsolationForest(
            n_estimators=200,
            contamination=contaminacion,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])
    t0 = time.perf_counter()
    pipe.fit(X_train)
    print(f"    entrenado en {time.perf_counter() - t0:.1f}s")
    return pipe


def puntuar_iforest(pipe, X):
    """Convierte la salida del IForest en una puntuacion 0-1 (mayor = mas anomalo).

    score_samples devuelve valores negativos donde MENOR es mas anomalo; se
    invierte el signo y se normaliza para que sea comparable con la
    probabilidad que devuelve XGBoost.
    """
    bruto = -pipe.named_steps["iforest"].score_samples(
        pipe.named_steps["escalado"].transform(X)
    )
    lo, hi = bruto.min(), bruto.max()
    return (bruto - lo) / (hi - lo) if hi > lo else np.zeros_like(bruto)


def main():
    MODELS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    print("=" * 66)
    print("  ENTRENAMIENTO DEL DETECTOR - Fase 2")
    print("=" * 66)

    df = cargar_dataset()
    print(f"\n  Dataset: {len(df):,} transacciones | "
          f"{int(df['Class'].sum())} fraudes ({df['Class'].mean() * 100:.3f}%)")
    print(f"  Variables ({len(FEATURE_COLS)}): V1-V28 (PCA) + Amount + Hour")
    print("  Nota: 'Time' se usa para ordenar y derivar Hour, no como predictor.")

    resultados = []

    for nombre_split, funcion_split in SPLITS.items():
        print(f"\n{'-' * 66}")
        print(f"  SPLIT: {nombre_split.upper()}")
        print(f"{'-' * 66}")

        X_train, X_test, y_train, y_test = funcion_split(df)
        print(resumen_split(nombre_split, y_train, y_test))
        fraudes_test = int(y_test.sum())

        # --- XGBoost (supervisado) ---
        print("\n  [1/2] XGBoost")
        xgb_model = entrenar_xgboost(X_train, y_train)
        score_xgb = xgb_model.predict_proba(X_test)[:, 1]
        r = evaluar(y_test, score_xgb, umbral=0.5, nombre="XGBoost")
        r["split"] = nombre_split
        imprimir(r, fraudes_test)
        resultados.append(r)

        # --- Isolation Forest (no supervisado) ---
        print("\n  [2/2] Isolation Forest")
        contaminacion = float(y_train.mean())
        iforest = entrenar_iforest(X_train, contaminacion)
        score_if = puntuar_iforest(iforest, X_test)
        # El umbral no puede ser 0.5: se fija en el cuantil que corresponde a
        # la contaminacion esperada, que es como opera un IForest en la practica.
        umbral_if = float(np.quantile(score_if, 1 - contaminacion))
        r = evaluar(y_test, score_if, umbral=umbral_if, nombre="IsolationForest")
        r["split"] = nombre_split
        imprimir(r, fraudes_test)
        resultados.append(r)

        # Persistir los modelos del split temporal, que es el realista y el que
        # usaran los agentes en la Fase 3.
        if nombre_split == "temporal":
            xgb_model.save_model(MODELS_DIR / "xgboost_fraude.json")
            joblib.dump(iforest, MODELS_DIR / "iforest_fraude.pkl")
            print(f"\n  Modelos guardados en {MODELS_DIR}")

    # --- Comparativa final ---
    print(f"\n{'=' * 66}")
    print("  COMPARATIVA")
    print(f"{'=' * 66}\n")
    tabla = tabla_comparativa(resultados)
    print(tabla)

    (REPORTS_DIR / "metricas_detector.md").write_text(
        "# Metricas del detector — Fase 2\n\n"
        "AUC-PR es la metrica principal: con una prevalencia del 0,173 %, "
        "su linea base es 0,0017.\n\n" + tabla + "\n",
        encoding="utf-8",
    )
    (REPORTS_DIR / "metricas_detector.json").write_text(
        json.dumps(resultados, indent=2, default=float), encoding="utf-8"
    )
    print(f"\n  Informe -> {REPORTS_DIR / 'metricas_detector.md'}")


if __name__ == "__main__":
    main()
