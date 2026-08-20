"""
Entrenamiento del detector sobre el dataset Sparkov (extension exploratoria).

Reutiliza las funciones de evaluacion de src.detector.metrics para que las
cifras sean comparables sin duplicar codigo. Entrena solo XGBoost: el objetivo
de esta extension no es repetir la comparativa de tres modelos del capitulo 5,
sino comprobar si un dataset con variables de negocio cambia lo que se puede
explicar. Ese punto ya quedo resuelto en 4.3 y 5.1 para el dataset principal.

Uso:
    python scripts/sparkov/entrenar_detector.py
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import OneHotEncoder

import sys
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.detector.metrics import evaluar, imprimir, tabla_comparativa  # noqa: E402

DATOS = ROOT / "data" / "sparkov"
MODELOS = ROOT / "models"
REPORTES = ROOT / "reports"

NUMERICAS = ["importe", "hora", "dia_semana", "edad", "distancia_km", "poblacion_ciudad"]
CATEGORICA = "categoria"
OBJETIVO = "es_fraude"


def construir_variables(train: pd.DataFrame, test: pd.DataFrame):
    """One-hot sobre categoria + variables numericas de negocio.

    A diferencia del dataset ULB, aqui cada columna tiene un nombre que un
    lector reconoce: "categoria_shopping_net", "distancia_km", "hora". La
    pregunta que motiva esta extension es si eso cambia lo que la capa 2
    puede explicar.
    """
    cod = OneHotEncoder(sparse_output=False, handle_unknown="ignore", dtype=np.float32)
    cod.fit(train[[CATEGORICA]])
    nombres_cat = [f"categoria_{c}" for c in cod.categories_[0]]

    def transformar(df):
        cat = pd.DataFrame(cod.transform(df[[CATEGORICA]]), columns=nombres_cat, index=df.index)
        return pd.concat([df[NUMERICAS].reset_index(drop=True),
                           cat.reset_index(drop=True)], axis=1)

    X_train = transformar(train)
    X_test = transformar(test)
    return X_train, X_test, list(X_train.columns)


def entrenar_xgboost(X_train, y_train, columnas):
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    spw = n_neg / n_pos
    print(f"    scale_pos_weight = {n_neg:,}/{n_pos} = {spw:.1f}")

    modelo = xgb.XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=spw, eval_metric="aucpr",
        tree_method="hist", n_jobs=-1, random_state=42,
    )
    t0 = time.perf_counter()
    modelo.fit(X_train, y_train)
    print(f"    entrenado en {time.perf_counter() - t0:.1f}s")
    return modelo


def contribuciones_legibles(modelo, X, columnas, idx, top=6):
    """Contribuciones por variable (pred_contribs) para un caso, en texto.

    Analogo al expediente que la capa 2 recibe en el sistema principal
    (4.3.4), pero con nombres de variable de negocio en lugar de V1..V28.
    """
    booster = modelo.get_booster()
    dm = xgb.DMatrix(X.iloc[[idx]], feature_names=columnas)
    contrib = booster.predict(dm, pred_contribs=True)[0]
    pares = list(zip(columnas + ["sesgo_base"], contrib))
    pares.sort(key=lambda p: -abs(p[1]))
    return pares[:top]


def main():
    print("=" * 66)
    print("  ENTRENAMIENTO DEL DETECTOR SOBRE SPARKOV")
    print("=" * 66)

    train = pd.read_csv(DATOS / "train.csv")
    test = pd.read_csv(DATOS / "test.csv")
    print(f"\n  train: {len(train):,} ({int(train[OBJETIVO].sum())} fraudes)")
    print(f"  test : {len(test):,} ({int(test[OBJETIVO].sum())} fraudes)")

    X_train, X_test, columnas = construir_variables(train, test)
    y_train, y_test = train[OBJETIVO], test[OBJETIVO]
    print(f"  variables ({len(columnas)}): {columnas}")

    modelo = entrenar_xgboost(X_train, y_train, columnas)
    score = modelo.predict_proba(X_test)[:, 1]
    r = evaluar(y_test, score, umbral=0.5, nombre="XGBoost-Sparkov")
    r["split"] = "temporal"
    imprimir(r, int(y_test.sum()))

    # --- Contribuciones de negocio para los primeros casos de fraude real ---
    print("\n  --- Ejemplos de contribuciones (fraude real, top score) ---")
    test_ord = test.reset_index(drop=True)
    idx_fraude = test_ord.index[test_ord[OBJETIVO] == 1].tolist()
    orden_score = np.argsort(-score)
    idx_fraude_detectado = [i for i in orden_score if i in idx_fraude][:5]

    ejemplos = []
    for i in idx_fraude_detectado:
        fila = test_ord.iloc[i]
        contrib = contribuciones_legibles(modelo, X_test, columnas, i)
        print(f"\n  Caso: {fila['comercio']} | {fila['categoria']} | "
              f"{fila['importe']:.2f} | distancia {fila['distancia_km']:.1f} km | "
              f"probabilidad {score[i]:.4f}")
        for var, val in contrib:
            print(f"    {var:<28} {val:+.4f}")
        ejemplos.append({
            "comercio": fila["comercio"], "categoria": fila["categoria"],
            "importe": float(fila["importe"]), "hora": float(fila["hora"]),
            "edad": float(fila["edad"]), "distancia_km": float(fila["distancia_km"]),
            "poblacion_ciudad": int(fila["poblacion_ciudad"]),
            "probabilidad": float(score[i]),
            "contribuciones": [[v, float(c)] for v, c in contrib],
        })

    MODELOS.mkdir(exist_ok=True)
    REPORTES.mkdir(exist_ok=True)
    modelo.save_model(MODELOS / "xgboost_sparkov.json")

    tabla = tabla_comparativa([r])
    (REPORTES / "sparkov_metricas.md").write_text(
        "# Extension exploratoria: detector sobre dataset Sparkov\n\n"
        "Dataset simulado con variables de negocio (comercio, categoria, "
        "distancia domicilio-comercio, edad), un ano de periodo, particion "
        "temporal con los ultimos dos meses como prueba.\n\n" + tabla + "\n",
        encoding="utf-8",
    )
    (REPORTES / "sparkov_metricas.json").write_text(
        json.dumps({"metricas": r, "ejemplos_contribuciones": ejemplos},
                   indent=2, default=float),
        encoding="utf-8",
    )
    print(f"\n  Modelo -> {MODELOS / 'xgboost_sparkov.json'}")
    print(f"  Informe -> {REPORTES / 'sparkov_metricas.md'}")


if __name__ == "__main__":
    main()
