"""
Reimprime las metricas del detector desde reports/metricas_detector.json.

Existe para poder capturar por consola las cifras del capitulo 4 sin
reentrenar nada: lee el fichero que produjo el entrenamiento, que es la misma
fuente que citan las tablas de la memoria.

Uso:
    python scripts/metricas.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import REPORTS_DIR  # noqa: E402

fichero = REPORTS_DIR / "metricas_detector.json"
if not fichero.exists():
    print(f"  No existe {fichero}. Entrena primero el detector.")
    sys.exit(1)

filas = json.loads(fichero.read_text(encoding="utf-8"))

print("=" * 74)
print("  METRICAS DEL DETECTOR  (reports/metricas_detector.json)")
print("=" * 74)
print(f"\n  {'modelo':<17}{'particion':<11}{'AUC-PR':>8}{'ROC-AUC':>9}"
      f"{'precision':>11}{'recall':>8}{'P@50':>7}{'P@100':>8}")
print("  " + "-" * 72)
for f in filas:
    print(f"  {f['modelo']:<17}{f['split']:<11}{f['auc_pr']:>8.3f}"
          f"{f['roc_auc']:>9.3f}{f['precision']:>11.3f}{f['recall']:>8.3f}"
          f"{f['precision@50']:>7.2f}{f['precision@100']:>8.2f}")

alea = [f for f in filas if f["split"] == "aleatorio"]
if alea:
    prev = alea[0]["prevalencia"]
    print(f"\n  Prevalencia del fraude: {prev:.4%}  "
          f"(linea base de AUC-PR = {prev:.4f})")
    xgb = next((f for f in alea if f["modelo"] == "XGBoost"), None)
    if xgb:
        print(f"  XGBoost, particion aleatoria: {xgb['tp']} aciertos, "
              f"{xgb['fp']} falsas alarmas, {xgb['fn']} fraudes perdidos "
              f"de {xgb['tp'] + xgb['fn']}")
