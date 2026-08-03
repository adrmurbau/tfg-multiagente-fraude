"""
Ablacion de grupos de variables del detector - capa 1.

Mide cuanto aporta cada bloque de informacion entrenando el detector con y sin
el. Responde a una limitacion declarada en la memoria y sin resolver.

## La duda concreta

`Hour` se deriva como el resto de dividir `Time` entre 3.600 respecto a 24, y
se incluye porque el fraude se concentra de madrugada. Pero el conjunto abarca
solo 48 horas, y en la particion temporal el conjunto de prueba cubre apenas
las ultimas horas: alli la variable es casi constante y no puede discriminar.

Cabe entonces que no aporte, o que reste, induciendo al modelo a aprender un
patron horario que no se sostiene fuera del periodo observado. Nunca se habia
medido, y afirmarlo sin medirlo seria justo lo que este trabajo critica.

## Que se compara

  completo    V1-V28 + Amount + Hour   configuracion actual
  sin_hour    V1-V28 + Amount          la duda concreta
  sin_amount  V1-V28 + Hour            control: ¿aporta el importe?
  solo_pca    V1-V28                   ¿basta con las componentes?

Los dos ultimos no responden a ninguna duda pendiente, pero salen gratis y
delimitan cuanta informacion vive fuera del anonimizado. Si `solo_pca` rinde
igual que `completo`, las dos variables interpretables son decorativas -y eso
tendria consecuencias para la capa 2, que las usa en sus explicaciones-.

Todo lo demas se mantiene fijo: misma configuracion de XGBoost, mismas
particiones, misma semilla. La unica variable es el conjunto de columnas.

Uso:
    python scripts/ablacion_variables.py
    python scripts/ablacion_variables.py --split aleatorio
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PCA_COLS, RANDOM_STATE, REPORTS_DIR  # noqa: E402
from src.detector.data import SPLITS, cargar_dataset  # noqa: E402

TOP_N = (20, 50, 100, 200)

GRUPOS = {
    "completo":   list(PCA_COLS) + ["Amount", "Hour"],
    "sin_hour":   list(PCA_COLS) + ["Amount"],
    "sin_amount": list(PCA_COLS) + ["Hour"],
    "solo_pca":   list(PCA_COLS),
}


def parsear_args():
    p = argparse.ArgumentParser(description="Ablacion de grupos de variables")
    p.add_argument("--split", choices=list(SPLITS), default="temporal")
    return p.parse_args()


def entrenar_y_evaluar(df, split, columnas):
    """Entrena con el subconjunto de columnas y devuelve las metricas.

    Se reimplementa la particion en lugar de reutilizar SPLITS porque hace
    falta controlar que columnas entran, y SPLITS devuelve ya las matrices con
    FEATURE_COLS fijo.
    """
    from src.config import TARGET_COL, TEST_SIZE

    if split == "temporal":
        orden = df.sort_values("Time", kind="mergesort")
        corte = int(len(orden) * (1 - TEST_SIZE))
        tr, te = orden.iloc[:corte], orden.iloc[corte:]
    else:
        from sklearn.model_selection import train_test_split
        tr, te = train_test_split(df, test_size=TEST_SIZE,
                                  random_state=RANDOM_STATE,
                                  stratify=df[TARGET_COL])

    X_tr, y_tr = tr[columnas], tr[TARGET_COL]
    X_te, y_te = te[columnas], te[TARGET_COL]
    spw = int((y_tr == 0).sum()) / int((y_tr == 1).sum())

    modelo = xgb.XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
        eval_metric="aucpr", tree_method="hist",
        n_jobs=-1, random_state=RANDOM_STATE,
    )
    modelo.fit(X_tr, y_tr)

    s = modelo.predict_proba(X_te)[:, 1]
    y = np.asarray(y_te)
    return {
        "n_variables": len(columnas),
        "auc_pr": float(average_precision_score(y, s)),
        "roc_auc": float(roc_auc_score(y, s)),
        "p_at_n": {n: float(y[np.argsort(-s)[:n]].mean()) for n in TOP_N},
    }


def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("  ABLACION DE GRUPOS DE VARIABLES")
    print("=" * 70)
    print(f"  Particion: {args.split}\n")

    df = cargar_dataset()
    resultados = {}

    for nombre, columnas in GRUPOS.items():
        r = entrenar_y_evaluar(df, args.split, columnas)
        resultados[nombre] = r
        print(f"  {nombre:<12} {r['n_variables']:>2} variables | "
              f"AUC-PR {r['auc_pr']:.4f} | P@50 {r['p_at_n'][50]:.3f}")

    base = resultados["completo"]["auc_pr"]
    print("\n" + "=" * 70)
    print("  APORTACION DE CADA BLOQUE")
    print("=" * 70 + "\n")
    print(f"  {'configuracion':<12}{'AUC-PR':>9}{'delta':>9}{'P@50':>8}"
          f"{'P@100':>8}  lectura")
    print("  " + "-" * 68)
    for nombre, r in resultados.items():
        d = r["auc_pr"] - base
        if nombre == "completo":
            lectura = "referencia"
        elif abs(d) < 0.005:
            lectura = "sin efecto apreciable"
        elif d < 0:
            lectura = f"quitarlo EMPEORA {abs(d):.3f}"
        else:
            lectura = f"quitarlo MEJORA {d:.3f}"
        print(f"  {nombre:<12}{r['auc_pr']:>9.4f}{d:>+9.4f}"
              f"{r['p_at_n'][50]:>8.3f}{r['p_at_n'][100]:>8.3f}  {lectura}")

    print("\n  Lectura de la ablacion:")
    d_hour = resultados["sin_hour"]["auc_pr"] - base
    if abs(d_hour) < 0.005:
        print("    Hour no aporta ni resta de forma apreciable. Mantenerla es")
        print("    inocuo, pero la justificacion de incluirla no se sostiene")
        print("    sobre estos datos y conviene reformularla en la memoria.")
    elif d_hour > 0:
        print("    Quitar Hour MEJORA el resultado: la variable esta")
        print("    perjudicando. El modelo aprende un patron horario que no")
        print("    generaliza fuera del periodo observado.")
    else:
        print("    Hour aporta de verdad. La decision de derivarla queda")
        print("    justificada con datos y no solo con el argumento teorico.")

    d_pca = resultados["solo_pca"]["auc_pr"] - base
    print()
    if abs(d_pca) < 0.01:
        print("    Las 28 componentes bastan: importe y hora apenas anaden")
        print("    nada. Tiene consecuencias para la capa 2, cuyas")
        print("    explicaciones se apoyan precisamente en esas dos.")
    else:
        print(f"    Importe y hora aportan {abs(d_pca):.3f} de AUC-PR sobre las")
        print("    componentes solas. Son las dos unicas variables")
        print("    interpretables y ademas aportan senal.")

    destino = REPORTS_DIR / f"ablacion_variables_{args.split}.json"
    destino.write_text(json.dumps({
        "split": args.split,
        "grupos": {k: v for k, v in GRUPOS.items()},
        "resultados": resultados,
    }, indent=2), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")


if __name__ == "__main__":
    main()
