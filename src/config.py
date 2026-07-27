"""
Configuracion central del proyecto.

Todo lo que sea una ruta, un nombre de modelo o una constante del dominio
vive aqui, para que ni el detector ni los agentes lleven rutas a pelo.
"""

from pathlib import Path

# --- Rutas ---
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"

DATASET_CSV = DATA_DIR / "creditcard.csv"

# --- LLM local (Ollama) ---
OLLAMA_HOST = "http://localhost:11434"
LLM_MODEL = "llama3.1:8b"       # Fase 1. Alternativa mas capaz: "qwen2.5:14b"
LLM_TEMPERATURE = 0.1           # analistas deterministas, no creativos

# --- Dataset ULB Credit Card Fraud ---
# 284.807 transacciones, 492 fraudes (~0,172%).
# V1..V28 son componentes PCA anonimizados; Time y Amount son originales.
TARGET_COL = "Class"
TIME_COL = "Time"

# 'Time' NO se usa como variable predictora: son segundos transcurridos desde la
# primera transaccion, asi que en el split temporal los valores de test caen
# fuera del rango visto en entrenamiento y el arbol no puede extrapolar. Se usa
# solo para ordenar y para derivar la hora del dia, que si es informativa
# (el fraude se concentra de madrugada).
PCA_COLS = [f"V{i}" for i in range(1, 29)]
FEATURE_COLS = PCA_COLS + ["Amount", "Hour"]

EXPECTED_ROWS = 284_807
EXPECTED_FRAUD = 492

# --- Detector ---
RANDOM_STATE = 42
TEST_SIZE = 0.2

# Numero de casos que un equipo de fraude real revisaria a mano por lote.
# La metrica que de verdad importa en operacion: de los N mas sospechosos,
# cuantos eran fraude.
TOP_N = [50, 100, 200]

# --- Semaforo de riesgo (umbrales sobre la probabilidad del detector) ---
RISK_THRESHOLDS = {
    "ALTO": 0.80,    # rojo
    "MEDIO": 0.40,   # ambar
}                     # por debajo de MEDIO -> verde
