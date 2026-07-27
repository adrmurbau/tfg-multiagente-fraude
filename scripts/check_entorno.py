"""
Verificacion del entorno - Fase 1 del TFG.

Comprueba las dos patas del sistema por separado:
  1. Capa de agentes -> el LLM local responde via Ollama y corre en GPU.
  2. Capa de detector -> el dataset ULB carga y tiene la forma esperada.

Uso:
    python scripts/check_entorno.py

Sin dependencias mas alla de pandas: las llamadas a Ollama van con urllib
(stdlib) a proposito, para que este script funcione aunque el resto del
entorno este a medias.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    DATASET_CSV,
    EXPECTED_FRAUD,
    EXPECTED_ROWS,
    LLM_MODEL,
    OLLAMA_HOST,
    TARGET_COL,
)

OK, FAIL, WARN = "[OK]  ", "[FALLO]", "[AVISO]"
fallos = []


def titulo(txt):
    print(f"\n{'=' * 62}\n  {txt}\n{'=' * 62}")


def _get(path, payload=None, timeout=120):
    url = f"{OLLAMA_HOST}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ----------------------------------------------------------------------
# 1. Python
# ----------------------------------------------------------------------
titulo("1. INTERPRETE PYTHON")
v = sys.version_info
print(f"      Version    : {v.major}.{v.minor}.{v.micro}")
print(f"      Ejecutable : {sys.executable}")

if (v.major, v.minor) == (3, 12):
    print(f"{OK}Python 3.12, la version recomendada para CrewAI.")
elif (v.major, v.minor) >= (3, 13):
    print(f"{WARN}Python {v.major}.{v.minor}: CrewAI puede fallar al instalar. Usa 3.12.")
else:
    print(f"{WARN}Python {v.major}.{v.minor}: por debajo de lo recomendado (3.12).")

if "WindowsApps" in sys.executable:
    print(f"{FAIL} Estas usando el Python de Microsoft Store (sandboxado).")
    print("        Recrea el venv con: py -3.12 -m venv .venv")
    fallos.append("Python de Microsoft Store")

if sys.prefix == sys.base_prefix:
    print(f"{WARN}No parece que el venv este activado.")
else:
    print(f"{OK}Venv activo en {sys.prefix}")


# ----------------------------------------------------------------------
# 2. Ollama: servicio y modelos
# ----------------------------------------------------------------------
titulo("2. OLLAMA - SERVICIO Y MODELOS")
modelo_presente = False
try:
    tags = _get("/api/tags", timeout=10)
    disponibles = [m["name"] for m in tags.get("models", [])]
    print(f"{OK}Ollama responde en {OLLAMA_HOST}")
    print(f"      Modelos descargados: {disponibles or '(ninguno)'}")

    modelo_presente = any(m == LLM_MODEL or m.startswith(LLM_MODEL.split(':')[0]) for m in disponibles)
    if modelo_presente:
        print(f"{OK}El modelo objetivo '{LLM_MODEL}' esta disponible.")
    else:
        print(f"{FAIL} Falta '{LLM_MODEL}'. Ejecuta:  ollama pull {LLM_MODEL}")
        fallos.append(f"modelo {LLM_MODEL} no descargado")

except urllib.error.URLError as e:
    print(f"{FAIL} No hay respuesta en {OLLAMA_HOST} -> {e}")
    print("        Arranca el servicio con:  ollama serve")
    fallos.append("Ollama no responde")


# ----------------------------------------------------------------------
# 3. Ollama: inferencia real + uso de GPU
# ----------------------------------------------------------------------
if modelo_presente:
    titulo("3. OLLAMA - INFERENCIA DE PRUEBA")
    prompt = (
        "Eres un analista de fraude. Responde SOLO con una palabra: "
        "si una tarjeta hace 40 compras de 1 euro en 3 minutos en paises distintos, "
        "clasifica el patron como NORMAL o SOSPECHOSO."
    )
    try:
        print(f"      Prompt: {prompt[:70]}...")
        t0 = time.perf_counter()
        r = _get("/api/generate", {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 30},
        })
        dt = time.perf_counter() - t0

        print(f"      Respuesta: {r.get('response', '').strip()[:200]}")
        print(f"      Latencia total: {dt:.1f}s")

        n_tok = r.get("eval_count", 0)
        ns = r.get("eval_duration", 0)
        if n_tok and ns:
            tps = n_tok / (ns / 1e9)
            print(f"      Velocidad: {tps:.1f} tokens/s ({n_tok} tokens)")
            if tps < 15:
                print(f"{WARN}Por debajo de 15 tok/s: sospecha de inferencia en CPU.")
            else:
                print(f"{OK}Velocidad coherente con inferencia en GPU.")
        print(f"{OK}El LLM local responde.")

        # Confirmacion directa de que el modelo esta cargado en VRAM
        ps = _get("/api/ps", timeout=10)
        for m in ps.get("models", []):
            total, vram = m.get("size", 0), m.get("size_vram", 0)
            pct = (vram / total * 100) if total else 0
            print(f"      '{m['name']}': {vram / 1e9:.1f} GB en VRAM de {total / 1e9:.1f} GB ({pct:.0f}%)")
            if pct < 90:
                print(f"{WARN}Parte del modelo esta en RAM, no en la GPU.")
            else:
                print(f"{OK}Modelo integro en la GPU.")

    except Exception as e:
        print(f"{FAIL} La inferencia ha fallado -> {e}")
        fallos.append("inferencia Ollama")


# ----------------------------------------------------------------------
# 4. Dataset ULB
# ----------------------------------------------------------------------
titulo("4. DATASET ULB (creditcard.csv)")
if not DATASET_CSV.exists():
    print(f"{FAIL} No existe {DATASET_CSV}")
    print("        Descarga el dataset y dejalo en data/creditcard.csv")
    fallos.append("dataset ausente")
else:
    try:
        import pandas as pd
    except ImportError:
        print(f"{FAIL} pandas no esta instalado -> pip install -r requirements.txt")
        fallos.append("pandas ausente")
    else:
        mb = DATASET_CSV.stat().st_size / 1e6
        t0 = time.perf_counter()
        df = pd.read_csv(DATASET_CSV)
        dt = time.perf_counter() - t0
        print(f"{OK}CSV cargado ({mb:.0f} MB) en {dt:.1f}s")
        print(f"      Dimensiones: {df.shape[0]:,} filas x {df.shape[1]} columnas")

        if TARGET_COL not in df.columns:
            print(f"{FAIL} No existe la columna objetivo '{TARGET_COL}'.")
            print(f"        Columnas: {list(df.columns)[:8]}...")
            fallos.append("columna Class ausente")
        else:
            n_fraude = int(df[TARGET_COL].sum())
            ratio = n_fraude / len(df) * 100
            print(f"      Fraudes: {n_fraude:,} de {len(df):,} ({ratio:.3f}%)")
            print(f"      Ratio de desbalanceo: 1 fraude por cada {len(df) // max(n_fraude, 1):,} transacciones")

            if df.shape[0] == EXPECTED_ROWS and n_fraude == EXPECTED_FRAUD:
                print(f"{OK}Coincide exactamente con el dataset ULB de referencia.")
            else:
                print(f"{WARN}Esperaba {EXPECTED_ROWS:,} filas y {EXPECTED_FRAUD} fraudes.")
                print("        Puede ser una variante del dataset: revisa la fuente.")

            nulos = int(df.isnull().sum().sum())
            print(f"      Valores nulos: {nulos}")
            print(f"      Importe: min {df['Amount'].min():.2f} / "
                  f"mediana {df['Amount'].median():.2f} / max {df['Amount'].max():.2f}")


# ----------------------------------------------------------------------
titulo("RESUMEN")
if fallos:
    print(f"{FAIL} Entorno INCOMPLETO. Pendiente:")
    for f in fallos:
        print(f"        - {f}")
    sys.exit(1)

print(f"{OK}Entorno listo. Las dos capas responden.")
print("      Siguiente: Fase 2 - entrenar el detector (XGBoost + Isolation Forest).")
sys.exit(0)
