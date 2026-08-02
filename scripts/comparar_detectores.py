"""
Comparacion estadistica entre XGBoost y Random Forest - capa 1.

Motivacion. En la particion temporal Random Forest obtiene mejor AUC-PR que
XGBoost (0,820 frente a 0,797). Antes de concluir nada hay que responder dos
preguntas distintas, que es justo lo que hace este script:

  1. ¿La diferencia es real o cabe dentro del ruido de muestreo?
     -> bootstrap pareado estratificado sobre el conjunto de test.

  2. Si es real, ¿importa?
     -> Precision@N en la cabeza del ranking, que es lo unico que un equipo
        de revision llega a mirar en un turno.

El resultado es un buen ejemplo de que significacion estadistica y relevancia
operativa no son lo mismo: la ventaja de Random Forest existe, pero vive en la
cola del ranking, que nadie revisa.

Por que bootstrap ESTRATIFICADO: con 75 fraudes sobre 56.962 transacciones, un
remuestreo simple produciria replicas con un numero muy variable de positivos
-y alguna con ninguno-, lo que dispararia la varianza de AUC-PR por una razon
ajena al modelo. Remuestreando por separado positivos y negativos se conserva
la prevalencia y se mide lo que se quiere medir.

Por que PAREADO: los dos modelos se evaluan sobre exactamente las mismas
transacciones remuestreadas en cada replica. La dificultad de la muestra se
cancela y el intervalo se estrecha.

Uso:
    python scripts/comparar_detectores.py
    python scripts/comparar_detectores.py --split aleatorio --repeticiones 5000
"""

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MODELS_DIR, RANDOM_STATE, REPORTS_DIR  # noqa: E402
from src.detector.data import SPLITS, cargar_dataset  # noqa: E402
from src.detector.train import entrenar_random_forest, entrenar_xgboost  # noqa: E402

TOP_N = (20, 50, 100, 200)


def parsear_args():
    p = argparse.ArgumentParser(description="XGBoost frente a Random Forest")
    p.add_argument("--split", choices=list(SPLITS), default="temporal",
                   help="Particion a evaluar. Por defecto la temporal, que es "
                        "la realista.")
    p.add_argument("--repeticiones", type=int, default=2000,
                   help="Replicas de bootstrap.")
    p.add_argument("--reentrenar", action="store_true",
                   help="Entrena de nuevo en lugar de cargar models/. "
                        "Necesario si se evalua un split distinto al temporal.")
    return p.parse_args()


def precision_en_n(y, score, n):
    """Proporcion de fraude entre las n transacciones peor puntuadas."""
    return float(y[np.argsort(-score)[:n]].mean())


def bootstrap_pareado(y, score_a, score_b, b=2000, semilla=RANDOM_STATE):
    """Distribucion de la diferencia de AUC-PR (b menos a).

    Devuelve el vector de diferencias, no un resumen: quien llama decide que
    percentiles quiere.
    """
    rng = np.random.default_rng(semilla)
    pos = np.where(y == 1)[0]
    neg = np.where(y == 0)[0]

    difs = np.empty(b)
    for k in range(b):
        idx = np.concatenate([
            rng.choice(pos, len(pos), replace=True),
            rng.choice(neg, len(neg), replace=True),
        ])
        difs[k] = (average_precision_score(y[idx], score_b[idx])
                   - average_precision_score(y[idx], score_a[idx]))
    return difs


def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)

    print("=" * 66)
    print("  XGBOOST FRENTE A RANDOM FOREST")
    print("=" * 66)
    print(f"  Particion    : {args.split}")
    print(f"  Repeticiones : {args.repeticiones}")

    df = cargar_dataset()
    X_train, X_test, y_train, y_test = SPLITS[args.split](df)
    y = np.asarray(y_test)

    rf_path = MODELS_DIR / "random_forest_fraude.pkl"
    usar_guardados = (not args.reentrenar and args.split == "temporal"
                      and rf_path.exists())

    if usar_guardados:
        print("\n  Cargando los modelos de models/ (particion temporal).")
        modelo_xgb = xgb.XGBClassifier()
        modelo_xgb.load_model(MODELS_DIR / "xgboost_fraude.json")
        modelo_rf = joblib.load(rf_path)
    else:
        print("\n  Entrenando ambos modelos...")
        modelo_xgb = entrenar_xgboost(X_train, y_train)
        modelo_rf = entrenar_random_forest(X_train, y_train)

    s_xgb = modelo_xgb.predict_proba(X_test)[:, 1]
    s_rf = modelo_rf.predict_proba(X_test)[:, 1]

    ap_x = average_precision_score(y, s_xgb)
    ap_r = average_precision_score(y, s_rf)

    print(f"\n  Test: {len(y):,} transacciones | {int(y.sum())} fraudes "
          f"({y.mean():.3%})")
    print(f"\n  {'':<16}{'AUC-PR':>10}{'ROC-AUC':>10}")
    print("  " + "-" * 36)
    print(f"  {'XGBoost':<16}{ap_x:>10.4f}{roc_auc_score(y, s_xgb):>10.4f}")
    print(f"  {'RandomForest':<16}{ap_r:>10.4f}{roc_auc_score(y, s_rf):>10.4f}")

    # --- 1. ¿La diferencia es real? ---
    print(f"\n  Bootstrap pareado estratificado (B = {args.repeticiones})...")
    difs = bootstrap_pareado(y, s_xgb, s_rf, args.repeticiones)
    lo, hi = np.percentile(difs, [2.5, 97.5])
    significativa = lo > 0 or hi < 0

    print(f"\n  Diferencia de AUC-PR (RandomForest menos XGBoost):")
    print(f"    observada    : {ap_r - ap_x:+.4f}")
    print(f"    media boot.  : {difs.mean():+.4f}")
    print(f"    IC 95 %      : [{lo:+.4f}, {hi:+.4f}]")
    print(f"    P(RF > XGB)  : {(difs > 0).mean():.1%}")
    print(f"    -> {'DIFERENCIA SIGNIFICATIVA' if significativa else 'EL IC INCLUYE EL CERO: no se afirma diferencia'}")

    # --- 2. ¿Importa? ---
    print(f"\n  Precision@N — la cabeza del ranking, que es lo que se revisa:")
    print(f"  {'N':>6}{'XGBoost':>12}{'RandomForest':>15}{'diferencia':>13}")
    print("  " + "-" * 46)
    tabla_n = []
    for n in TOP_N:
        px, pr = precision_en_n(y, s_xgb, n), precision_en_n(y, s_rf, n)
        tabla_n.append({"n": n, "xgboost": px, "random_forest": pr})
        print(f"  {n:>6}{px:>12.3f}{pr:>15.3f}{pr - px:>+13.3f}")

    # Tolerancia en Precision@N: 0,02 sobre n=50 es UN fraude de cincuenta.
    # Se compara con <=, no con <, porque una diferencia de exactamente un caso
    # no puede considerarse una ventaja operativa.
    # Se redondea antes de comparar: 1,000 - 0,980 da 0,020000000000000018 en
    # coma flotante, que fallaria la comprobacion contra 0,02 por un residuo
    # numerico y no por una diferencia real.
    brecha = round(max(abs(f["random_forest"] - f["xgboost"])
                       for f in tabla_n if f["n"] <= 100), 6)
    iguales = brecha <= 0.02
    ganador = "RandomForest" if difs.mean() > 0 else "XGBoost"
    elegido = "XGBoost"   # el que usa el detector en produccion

    print()
    if not significativa:
        print("  LECTURA: no hay evidencia de diferencia entre ambos modelos.")
    elif iguales:
        print(f"  LECTURA: {ganador} gana en AUC-PR y la diferencia es real,")
        print(f"  pero en la cabeza del ranking los dos modelos son")
        print(f"  indistinguibles (brecha maxima {brecha:.3f} hasta N=100).")
        print("  La ventaja vive en la cola, que ningun analista revisa:")
        print("  significacion estadistica sin relevancia operativa.")
    elif ganador == elegido:
        print(f"  LECTURA: gana {ganador}, que es el modelo elegido, y la")
        print("  ventaja se aprecia tambien en la cabeza del ranking.")
    else:
        print(f"  LECTURA: gana {ganador} tambien en la cabeza del ranking.")
        print(f"  Conviene reconsiderar el uso de {elegido} como detector.")

    salida = {
        "split": args.split,
        "n_test": int(len(y)),
        "fraudes_test": int(y.sum()),
        "auc_pr": {"xgboost": float(ap_x), "random_forest": float(ap_r)},
        "bootstrap": {
            "repeticiones": args.repeticiones,
            "diferencia_media": float(difs.mean()),
            "ic95": [float(lo), float(hi)],
            "prob_rf_mejor": float((difs > 0).mean()),
            "significativa": bool(significativa),
        },
        "precision_en_n": tabla_n,
        "brecha_max_hasta_n100": float(brecha),
        "equivalentes_operativamente": bool(iguales),
        "ganador_auc_pr": ganador,
    }
    destino = REPORTS_DIR / f"comparativa_detectores_{args.split}.json"
    destino.write_text(json.dumps(salida, indent=2), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")


if __name__ == "__main__":
    main()
