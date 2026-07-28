"""
Prueba del detector como herramienta - SIN LLM.

Valida que la capa 1 hace todo lo que los agentes le van a pedir. Si esto pasa
y la Fase 3 falla, el problema esta en el modelo de lenguaje, no aqui.

Uso:
    python scripts/test_detector.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import TARGET_COL  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_lote  # noqa: E402


def titulo(t):
    print(f"\n{'=' * 66}\n  {t}\n{'=' * 66}")


titulo("1. CARGA DE MODELOS")
det = DetectorFraude()
# n_estimators no sobrevive a load_model(); se lee del booster.
print(f"[OK]   XGBoost cargado ({det.booster.num_boosted_rounds()} arboles)")
print(f"[OK]   Isolation Forest: {'cargado' if det.iforest else 'NO disponible'}")

titulo("2. CONSTRUCCION DEL LOTE")
df = cargar_dataset()
lote = construir_lote(df, n=500, n_fraudes=5)
print(f"  Lote de {len(lote)} transacciones del periodo de test")
print(f"  Fraudes reales ocultos en el lote: {int(lote[TARGET_COL].sum())}")
print("  (las etiquetas viajan en el lote pero no las ve ni el detector ni los agentes)")

titulo("3. PUNTUACION Y SEMAFORO")
res = det.resumen_lote(lote)
for k, v in res.items():
    print(f"    {k:>20}: {v:,.2f}" if isinstance(v, float) else f"    {k:>20}: {v:,}")

titulo("4. TOP 10 SOSPECHOSAS")
top = det.top_sospechosas(lote, n=10)
print(f"    {'#':>4} {'prob':>8} {'riesgo':>7} {'importe':>10} {'hora':>6}  real")
for idx, fila in top.iterrows():
    marca = "FRAUDE" if fila[TARGET_COL] == 1 else "-"
    print(f"    {idx:>4} {fila['prob_fraude']:>8.4f} {fila['riesgo']:>7} "
          f"{fila['Amount']:>10.2f} {fila['Hour']:>6.1f}  {marca}")

aciertos = int(top[TARGET_COL].sum())
total = int(lote[TARGET_COL].sum())
print(f"\n  Precision@10 = {aciertos / 10:.2f} "
      f"({aciertos} de los {total} fraudes del lote en las 10 primeras)")

titulo("5. EXPLICACION DEL CASO MAS SOSPECHOSO")
print(det.explicar(lote, top.index[0]).a_texto())

titulo("6. CONTRASTE: UNA TRANSACCION DE RIESGO BAJO")
baja = det.puntuar(lote).nsmallest(1, "prob_fraude")
print(det.explicar(lote, baja.index[0]).a_texto())

print(f"\n{'=' * 66}")
print("  [OK]  El detector responde a todo lo que necesitan los agentes.")
print("        Siguiente: envolverlo como herramienta de CrewAI.")
print(f"{'=' * 66}")
