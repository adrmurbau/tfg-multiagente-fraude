"""
Prueba de las herramientas de CrewAI - SIN LLM.

Invoca cada herramienta directamente, igual que haria un agente, pero sin
modelo de lenguaje de por medio. Sirve para comprobar dos cosas:

  - que las salidas son legibles y auto-explicativas (si a ti te cuesta
    entenderlas, a un 8B le costara mas);
  - que los errores se comportan, porque un LLM SI va a pasar identificadores
    inventados y la herramienta tiene que reconducirlo en vez de reventar.

Uso:
    python scripts/test_tools.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.tools import (  # noqa: E402
    herramientas_disponibles,
    inicializar_contexto,
)
from src.config import TARGET_COL  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import construir_lote  # noqa: E402


def titulo(t):
    print(f"\n{'=' * 66}\n  {t}\n{'=' * 66}")


titulo("PREPARACION")
df = cargar_dataset()
lote = construir_lote(df, n=500, n_fraudes=5)
inicializar_contexto(lote)
print(f"  Lote de {len(lote)} transacciones "
      f"({int(lote[TARGET_COL].sum())} fraudes ocultos)")

t = herramientas_disponibles()

titulo("HERRAMIENTA 1 - estadisticas_del_lote")
print(t["estadisticas"]._run())

titulo("HERRAMIENTA 2 - priorizar_sospechosas(n=8)")
salida = t["priorizar"]._run(n=8)
print(salida)

# Recuperar un id real de la salida para encadenar, tal y como haria el agente
primer_id = int(salida.splitlines()[4].split()[0])

titulo(f"HERRAMIENTA 3 - explicar_transaccion({primer_id})")
print(t["explicar"]._run(id_transaccion=primer_id))

titulo("HERRAMIENTA 3b - MANEJO DE ERRORES (id inventado)")
print(t["explicar"]._run(id_transaccion=999999))

titulo("HERRAMIENTA 3c - MANEJO DE ERRORES (id no numerico)")
print(t["explicar"]._run(id_transaccion="la primera"))

titulo("HERRAMIENTA 4 - rendimiento_del_detector")
print(t["rendimiento"]._run())

titulo("LIMITES")
print("  priorizar_sospechosas(n=500) -> debe recortarse a 50:")
print("  " + t["priorizar"]._run(n=500).splitlines()[0])

print(f"\n{'=' * 66}")
print("  [OK]  Las cuatro herramientas responden y degradan con elegancia.")
print("        Siguiente: los seis agentes sobre estas herramientas.")
print(f"{'=' * 66}")
