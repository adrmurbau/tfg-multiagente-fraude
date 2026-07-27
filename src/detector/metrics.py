"""
Evaluacion del detector.

Con 1 fraude por cada 578 transacciones, la exactitud (accuracy) es inservible:
un modelo que responda siempre "no hay fraude" acierta el 99,83% de las veces.
Este modulo se apoya en metricas que si distinguen:

  - AUC-PR (average precision): area bajo la curva precision-recall. La metrica
    de referencia en deteccion de fraude. Su linea base no es 0,5 sino la
    prevalencia de la clase positiva (~0,0017 aqui), asi que cualquier valor
    por encima de 0,5 ya es un modelo muy competente.

  - Precision@N: de las N transacciones que el modelo marca como mas
    sospechosas, cuantas eran fraude de verdad. Es la metrica operativa: un
    equipo de fraude tiene capacidad limitada de revision manual.

  - ROC-AUC: se reporta porque la literatura lo usa, pero es optimista con
    clases desbalanceadas porque los verdaderos negativos lo inflan.
"""

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.config import TOP_N


def evaluar(y_true, y_score, umbral=0.5, nombre="modelo") -> dict:
    """Calcula el bloque completo de metricas para un vector de puntuaciones."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    y_pred = (y_score >= umbral).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    res = {
        "modelo": nombre,
        "auc_pr": average_precision_score(y_true, y_score),
        "roc_auc": roc_auc_score(y_true, y_score),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "prevalencia": float(y_true.mean()),
    }

    # Precision@N: ordenar por puntuacion descendente y mirar los N primeros
    orden = np.argsort(-y_score)
    for n in TOP_N:
        n_real = min(n, len(y_true))
        aciertos = int(y_true[orden[:n_real]].sum())
        res[f"precision@{n}"] = aciertos / n_real
        res[f"aciertos@{n}"] = aciertos

    return res


def imprimir(res: dict, total_fraudes: int = None):
    """Vuelca las metricas en un formato legible por consola."""
    print(f"\n  --- {res['modelo']} ---")
    print(f"    AUC-PR        : {res['auc_pr']:.4f}   "
          f"(linea base = {res['prevalencia']:.5f})")
    print(f"    ROC-AUC       : {res['roc_auc']:.4f}")
    print(f"    Precision     : {res['precision']:.4f}")
    print(f"    Recall        : {res['recall']:.4f}")
    print(f"    F1            : {res['f1']:.4f}")
    print(f"    Matriz        : TP={res['tp']}  FP={res['fp']}  "
          f"FN={res['fn']}  TN={res['tn']:,}")

    print("    Revision manual (precision@N):")
    for n in TOP_N:
        if f"precision@{n}" in res:
            extra = ""
            if total_fraudes:
                extra = f" | {res[f'aciertos@{n}'] / total_fraudes * 100:.0f}% del fraude total"
            print(f"      top {n:>3}: {res[f'precision@{n}']:.3f} "
                  f"({res[f'aciertos@{n}']} fraudes){extra}")


def tabla_comparativa(resultados: list) -> str:
    """Tabla en Markdown lista para pegar en la memoria."""
    cab = "| Modelo | Split | AUC-PR | ROC-AUC | Precision | Recall | F1 | P@100 |"
    sep = "|---|---|---|---|---|---|---|---|"
    filas = [
        f"| {r['modelo']} | {r.get('split', '-')} | {r['auc_pr']:.4f} | "
        f"{r['roc_auc']:.4f} | {r['precision']:.4f} | {r['recall']:.4f} | "
        f"{r['f1']:.4f} | {r.get('precision@100', float('nan')):.3f} |"
        for r in resultados
    ]
    return "\n".join([cab, sep, *filas])
