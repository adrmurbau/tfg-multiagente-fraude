"""
Busqueda de hiperparametros del detector - Fase 7.

Los hiperparametros del primer detector (400 arboles, profundidad 5,
learning_rate 0.1) se eligieron por criterio, no por experimentacion. Eran
valores razonables, pero "razonable" no es una justificacion defendible: la
pregunta legitima es "¿por que 400 y no 200?".

Este script responde esa pregunta con una busqueda aleatoria validada, y
—igual de importante— responde si la busqueda MEJORA algo. Un resultado
"los valores por defecto ya eran buenos" es perfectamente valido, pero solo
si esta medido.

DECISIONES METODOLOGICAS
------------------------

1. La busqueda usa SOLO datos de entrenamiento. El conjunto de test se
   reserva intacto para la comparacion final. Buscar hiperparametros mirando
   el test es una forma sutil de sobreajuste: acabarias eligiendo la
   configuracion que mejor memoriza tu test concreto.

2. Validacion cruzada distinta segun el split:
   - aleatorio -> StratifiedKFold, que preserva la proporcion de fraude en
     cada pliegue. Con 0,17 % de positivos, un pliegue sin estratificar
     podria quedarse casi sin fraudes.
   - temporal  -> TimeSeriesSplit, que entrena siempre con pasado y valida
     con futuro. Usar KFold normal sobre datos temporales filtraria
     informacion del futuro al entrenamiento.

3. Se optimiza AUC-PR (`average_precision` en scikit-learn), coherente con
   el resto del trabajo.

4. `scale_pos_weight` TAMBIEN se busca. Es una pregunta abierta interesante:
   la practica habitual es usar el ratio completo (~577), pero hay quien
   defiende su raiz cuadrada (~24) porque el ratio completo puede provocar
   demasiados falsos positivos. Merece medirse en lugar de asumirse.

Uso:
    python scripts/tune_detector.py                      # ambos splits
    python scripts/tune_detector.py --split temporal
    python scripts/tune_detector.py --iteraciones 100    # busqueda mas amplia
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import average_precision_score, precision_score, recall_score
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    TimeSeriesSplit,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RANDOM_STATE, REPORTS_DIR, TOP_N  # noqa: E402
from src.detector.data import SPLITS, cargar_dataset  # noqa: E402

# Hiperparametros actuales, los elegidos "por criterio". Son la referencia
# contra la que se compara: si la busqueda no los mejora, se documenta.
BASE = dict(
    n_estimators=400, max_depth=5, learning_rate=0.1,
    subsample=0.8, colsample_bytree=0.8,
)

ESPACIO = {
    "n_estimators": [100, 200, 400, 600, 800],
    "max_depth": [3, 4, 5, 6, 8, 10],
    "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.2, 0.3],
    "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
    # Numero minimo de muestras que debe tener una hoja. Sube -> mas
    # conservador, menos sobreajuste.
    "min_child_weight": [1, 3, 5, 10],
    # Ganancia minima para partir un nodo. Sube -> arboles mas simples.
    "gamma": [0, 0.1, 0.3, 0.5, 1.0],
}


def parsear_args():
    p = argparse.ArgumentParser(description="Busqueda de hiperparametros")
    p.add_argument("--split", choices=["aleatorio", "temporal", "ambos"],
                   default="ambos")
    p.add_argument("--iteraciones", type=int, default=50,
                   help="Combinaciones a probar (busqueda aleatoria).")
    p.add_argument("--cv", type=int, default=3, help="Pliegues de validacion.")
    return p.parse_args()


def evaluar_en_test(modelo, X_test, y_test) -> dict:
    """Metricas sobre el conjunto reservado, nunca visto en la busqueda."""
    score = modelo.predict_proba(X_test)[:, 1]
    pred = (score >= 0.5).astype(int)
    orden = np.argsort(-score)
    y = np.asarray(y_test)

    res = {
        "auc_pr": average_precision_score(y, score),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
    }
    for n in TOP_N:
        res[f"precision@{n}"] = float(y[orden[:n]].sum()) / n
    return res


def buscar(nombre_split, df, args) -> dict:
    print(f"\n{'=' * 66}")
    print(f"  SPLIT: {nombre_split.upper()}")
    print(f"{'=' * 66}")

    X_train, X_test, y_train, y_test = SPLITS[nombre_split](df)
    n_neg, n_pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    ratio = n_neg / n_pos

    # Tres estrategias de ponderacion, para medir cual funciona mejor
    espacio = dict(ESPACIO)
    espacio["scale_pos_weight"] = [1, round(np.sqrt(ratio), 1), round(ratio, 1)]

    print(f"  Entrenamiento : {len(X_train):,} ({n_pos} fraudes)")
    print(f"  Test          : {len(X_test):,} ({int(y_test.sum())} fraudes)")
    print(f"  scale_pos_weight candidatos: {espacio['scale_pos_weight']}")

    # La validacion cruzada respeta la naturaleza del split
    if nombre_split == "temporal":
        cv = TimeSeriesSplit(n_splits=args.cv)
        print(f"  Validacion    : TimeSeriesSplit({args.cv}) — pasado -> futuro")
    else:
        cv = StratifiedKFold(n_splits=args.cv, shuffle=True,
                             random_state=RANDOM_STATE)
        print(f"  Validacion    : StratifiedKFold({args.cv}) — proporcion preservada")

    # --- Referencia: los hiperparametros elegidos "por criterio" ---
    print("\n  [1/2] Entrenando la configuracion de referencia...")
    base = xgb.XGBClassifier(
        **BASE, scale_pos_weight=ratio, eval_metric="aucpr",
        tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
    )
    base.fit(X_train, y_train)
    met_base = evaluar_en_test(base, X_test, y_test)
    print(f"        AUC-PR en test: {met_base['auc_pr']:.4f}")

    # --- Busqueda aleatoria ---
    print(f"\n  [2/2] Probando {args.iteraciones} combinaciones "
          f"x {args.cv} pliegues = {args.iteraciones * args.cv} entrenamientos...")
    busqueda = RandomizedSearchCV(
        xgb.XGBClassifier(eval_metric="aucpr", tree_method="hist",
                          n_jobs=-1, random_state=RANDOM_STATE),
        param_distributions=espacio,
        n_iter=args.iteraciones,
        scoring="average_precision",   # = AUC-PR
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=1,        # XGBoost ya usa todos los nucleos internamente
        verbose=1,
        refit=True,
    )
    t0 = time.perf_counter()
    busqueda.fit(X_train, y_train)
    dt = time.perf_counter() - t0

    met_tuned = evaluar_en_test(busqueda.best_estimator_, X_test, y_test)
    mejora = met_tuned["auc_pr"] - met_base["auc_pr"]

    print(f"\n  Busqueda completada en {dt / 60:.1f} min")
    print(f"  Mejor AUC-PR en validacion cruzada: {busqueda.best_score_:.4f}")
    print("\n  Mejores hiperparametros:")
    for k, v in sorted(busqueda.best_params_.items()):
        marca = ""
        if k in BASE and BASE[k] != v:
            marca = f"   (antes: {BASE[k]})"
        print(f"    {k:<20}: {v}{marca}")

    print(f"\n  --- COMPARACION EN TEST (datos nunca vistos) ---")
    print(f"    {'metrica':<16}{'referencia':>12}{'ajustado':>12}{'delta':>10}")
    for k in ["auc_pr", "precision", "recall"] + [f"precision@{n}" for n in TOP_N]:
        d = met_tuned[k] - met_base[k]
        print(f"    {k:<16}{met_base[k]:>12.4f}{met_tuned[k]:>12.4f}{d:>+10.4f}")

    if mejora > 0.01:
        veredicto = "La busqueda MEJORA de forma apreciable la configuracion inicial."
    elif mejora > 0:
        veredicto = ("La busqueda mejora marginalmente. La configuracion inicial "
                     "ya estaba bien elegida.")
    else:
        veredicto = ("La busqueda NO mejora en test: la configuracion inicial era "
                     "tan buena o mejor. Posible sobreajuste a la validacion cruzada.")
    print(f"\n  >> {veredicto}")

    return {
        "split": nombre_split,
        "mejores_params": busqueda.best_params_,
        "auc_pr_cv": float(busqueda.best_score_),
        "metricas_referencia": met_base,
        "metricas_ajustado": met_tuned,
        "mejora_auc_pr": float(mejora),
        "veredicto": veredicto,
        "iteraciones": args.iteraciones,
        "minutos": round(dt / 60, 1),
    }


def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)

    print("=" * 66)
    print("  BUSQUEDA DE HIPERPARAMETROS DEL DETECTOR")
    print("=" * 66)
    print("  La busqueda usa SOLO datos de entrenamiento.")
    print("  El test se reserva para la comparacion final.")

    df = cargar_dataset()
    splits = ["aleatorio", "temporal"] if args.split == "ambos" else [args.split]
    resultados = [buscar(s, df, args) for s in splits]

    destino = REPORTS_DIR / "hiperparametros.json"
    destino.write_text(json.dumps(resultados, indent=2, default=float),
                       encoding="utf-8")

    # Tabla en Markdown para la memoria
    md = ["# Búsqueda de hiperparámetros del detector\n",
          "Búsqueda aleatoria sobre datos de entrenamiento, validada con "
          "validación cruzada. El conjunto de test permanece intacto hasta la "
          "comparación final.\n",
          "| Split | AUC-PR referencia | AUC-PR ajustado | Δ | Veredicto |",
          "|---|---|---|---|---|"]
    for r in resultados:
        md.append(f"| {r['split']} | {r['metricas_referencia']['auc_pr']:.4f} | "
                  f"{r['metricas_ajustado']['auc_pr']:.4f} | "
                  f"{r['mejora_auc_pr']:+.4f} | {r['veredicto']} |")
    md.append("\n## Mejores hiperparámetros por split\n")
    for r in resultados:
        md.append(f"### {r['split']}\n")
        md.append("```json")
        md.append(json.dumps(r["mejores_params"], indent=2))
        md.append("```\n")

    (REPORTS_DIR / "hiperparametros.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")
    print(f"  Tabla      -> {REPORTS_DIR / 'hiperparametros.md'}")
    print("\n  Si la mejora compensa, aplica los parametros en "
          "src/detector/train.py y reentrena.")


if __name__ == "__main__":
    main()
