# TFG — Sistema multi-agente para detección de fraude bancario

Un "departamento de analistas" formado por agentes LLM locales que prepara los
datos, entrena y consulta un detector de fraude, evalúa sus resultados, explica
cada caso sospechoso y emite un informe priorizado con semáforo de riesgo.

Autor: Adrián · Grado en Ingeniería Informática

## Arquitectura: dos capas

La distinción es el núcleo conceptual del trabajo, y conviene no confundirla:

| | Capa 1 — Detector | Capa 2 — Agentes |
|---|---|---|
| **Qué es** | Modelo tabular (XGBoost + Isolation Forest) | LLMs preentrenados locales (Ollama) |
| **¿Se entrena con los datos?** | **Sí**, desde cero | **No**, nunca |
| **Función** | Puntúa el riesgo de fraude | Razonan, coordinan y **usan** el detector como herramienta |
| **Analogía** | El instrumento de laboratorio | Los analistas que lo manejan e interpretan |

## El departamento

| Agente | Rol |
|---|---|
| Coordinador | Recibe el lote, delega, compila el informe final |
| Analista de datos | Explora y prepara datos, feature engineering, calidad |
| Modelador | Entrena y afina el detector ML |
| Evaluador | Mide resultados, vigila los falsos positivos |
| Investigador / Explicador | Explica por qué cada transacción es sospechosa (valores, SHAP) |
| Reportero | Redacta el informe priorizado con semáforo de riesgo |

## Stack

- **Python 3.12** (no 3.13: CrewAI arrastra dependencias que aún rompen)
- **Ollama** + `llama3.1:8b` — más adelante `qwen2.5:14b`
- **CrewAI** para la orquestación de agentes
- **XGBoost** (supervisado) + **Isolation Forest** (no supervisado) para el detector
- GPU: NVIDIA RTX 5060 Ti 16 GB

## Dataset

**Credit Card Fraud Detection** (ULB / Worldline, vía Kaggle): 284.807
transacciones europeas reales de septiembre de 2013, de las que 492 son fraude
(**0,172 %**). Las variables `V1`–`V28` son componentes PCA anonimizados por
confidencialidad; solo `Time` y `Amount` conservan su significado original.

El desbalanceo extremo es justamente lo que hace interesante el problema: la
exactitud (*accuracy*) es inútil aquí — un modelo que prediga "no hay fraude"
siempre acierta el 99,83 % de las veces. Por eso la evaluación se apoya en
**AUC-PR, precision, recall y F1**, más el análisis top-N.

El CSV **no se versiona** (licencia y tamaño). Va en `data/creditcard.csv`.

## Estructura

```
tfg-multiagente-fraude/
├── data/                 # dataset (ignorado por git)
├── models/               # modelos entrenados (ignorados)
├── reports/              # informes generados (ignorados)
├── src/
│   ├── config.py         # rutas, constantes, umbrales de riesgo
│   ├── detector/         # capa 1 — ML
│   └── agents/           # capa 2 — CrewAI
├── scripts/
│   └── check_entorno.py  # verificación del entorno (Fase 1)
└── notebooks/            # exploración
```

## Puesta en marcha

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.1:8b
# dejar creditcard.csv en data/
python scripts\check_entorno.py
```

## Hoja de ruta

1. **Entorno** — Ollama, dataset, venv con CrewAI ← *estamos aquí*
2. **Detector** — entrenar, evaluar y envolver como herramienta
3. **Agentes** — los 6 roles en CrewAI sobre LLM local
4. **Integración** — flujo end-to-end: lote → informe priorizado + explicaciones
5. **Evaluación y memoria** — métricas del sistema y casos demostrados
