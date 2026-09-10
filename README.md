# TFG — ¿Aporta algo una capa de agentes LLM sobre un detector de fraude?

Sistema de dos capas para detección de fraude con tarjeta, ejecutado
íntegramente en local, construido para responder a una pregunta concreta: si
poner un conjunto de agentes basados en modelos de lenguaje por encima de un
detector tabular mejora la detección, y qué capacidad necesitan esos modelos
para no empeorarla.

**El resultado principal es negativo y está medido.** La capa de agentes no
mejora la detección, y concederle autoridad para descartar casos la degrada.

Autor: Adrián · Grado en Ingeniería Informática · Universidad de Sevilla

---

## Las dos capas

| | Capa 1 — Detector | Capa 2 — Departamento |
|---|---|---|
| Qué es | XGBoost e Isolation Forest | Seis agentes sobre CrewAI |
| ¿Se entrena con los datos? | Sí, desde cero | No, nunca |
| Función | Puntuar y priorizar | Interpretar y redactar |
| Determinismo | Determinista | Estocástico |
| Coste por turno | Milisegundos | Minutos |

La capa 1 puntúa las transacciones de un turno y eleva a revisión las que
superan un umbral. La capa 2 recibe únicamente ese expediente y produce el
informe. Opera en dos modos: **interpreta**, donde explica sin decidir, y
**revisa**, donde se le concede autoridad para descartar casos.

La separación no es un detalle de implementación: es la hipótesis que el
trabajo pone a prueba.

## Qué se ha medido

| Pregunta | Respuesta |
|---|---|
| ¿Rinde el detector? | AUC-PR 0,883 aleatoria, 0,797 temporal. P@50 = 1,00 |
| ¿Mejora la capa 2 la detección? | No. En el mejor caso la deja igual |
| ¿Ayuda un modelo mayor? | Un 72B emite los mismos veredictos que un 14B, a 1.790 veces el coste |
| ¿Sirve la explicación para auditar? | No. Corregir la premisa cambia el texto y no la decisión |
| ¿Qué limita el sistema? | La capacidad de revisión del equipo, no el modelo |

El detalle está en `memoria/` y las cifras proceden de los ficheros de
`reports/`, todos versionados.

## Restricción de partida

Ejecución local, sin enviar datos a terceros y sin coste recurrente. No es una
limitación sufrida: es la premisa. El escenario que se modela es el de una
entidad que no puede mandar transacciones a un servicio externo.

Por eso la comparación con modelos de mayor capacidad se resolvió mediante
descomposición por capas, que permite ejecutar un modelo de 72.000 millones de
parámetros en una tarjeta de 16 GB, y no llamando a una interfaz remota.

## Estructura

```
tfg-multiagente-fraude/
├── data/        dataset (ignorado: licencia y tamaño)
├── models/      modelos entrenados (ignorados: se regeneran)
├── reports/     resultados de todas las ejecuciones (VERSIONADOS)
├── docs/        documentos de trabajo y estado del arte
├── memoria/     el texto de la memoria y el guion que lo compone a .docx
├── src/
│   ├── config.py      rutas, constantes y umbrales
│   ├── evaluacion.py  medida del sistema y auditoría de informes
│   ├── detector/      capa 1
│   └── agents/        capa 2
└── scripts/     un guion por experimento
```

Los resultados experimentales **sí** se versionan, deliberadamente: la memoria
cita cada uno como fuente de sus cifras y son irrepetibles, porque el modelo es
estocástico y una ejecución perdida no se reproduce.

## Guiones

**Sistema**

| Guion | Función |
|---|---|
| `check_entorno.py` | Verificación del entorno antes de nada |
| `run_departamento.py` | Ejecución completa sobre un turno |
| `run_streaming.py` | Operación en continuo por ventanas cortas |
| `tune_detector.py` | Búsqueda de hiperparámetros |

**Experimentos**

| Guion | Pregunta |
|---|---|
| `experimento.py` | Comparativa entre modelos y modos |
| `analisis.py` | Análisis estadístico de lo anterior |
| `comparar_detectores.py` | ¿Difieren XGBoost y Random Forest? |
| `ablacion_desbalanceo.py` | ¿Qué aporta cada estrategia frente al desbalanceo? |
| `ablacion_variables.py` | ¿Cuánto contribuye cada grupo de variables? |
| `ablacion_dominio.py` | ¿Cambia el veredicto al corregir la premisa, o solo la prosa? |
| `investigador_solo.py` | Comparación con modelos de mayor capacidad |

**Pruebas sin modelo de lenguaje**

`test_detector.py`, `test_tools.py`, `test_auditor.py`, `test_crew_minimo.py`,
`reauditar.py`

Que cuatro de los dieciséis guiones sean pruebas que no invocan al modelo no es
casual: los fallos de este tipo de sistema no lanzan excepciones, de modo que
la única defensa es comprobar de forma programática lo que devuelve.

## Conjunto de datos

**Credit Card Fraud Detection** (ULB / Worldline): 284.807 transacciones
europeas de septiembre de 2013, de las que 492 son fraude, un 0,172 %. Las
variables `V1`–`V28` son componentes principales anonimizadas; solo `Time` y
`Amount` conservan significado.

El desbalanceo extremo hace inútil la exactitud —predecir "no hay fraude"
siempre acierta el 99,83 % de las veces— y obliga a evaluar con AUC-PR y
precisión en los N primeros casos.

El CSV no se versiona. Va en `data/creditcard.csv`.

## Puesta en marcha

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.1:8b
# dejar creditcard.csv en data/
python scripts\check_entorno.py
```

Para la comparación con modelos que no caben en memoria hace falta un entorno
aparte, con PyTorch compilado para la arquitectura de la GPU. El guion
correspondiente lo comprueba antes de descargar nada y explica cómo crearlo.

## Formato de la memoria

El texto de la memoria está escrito en `memoria/content.js`, en Markdown
simple (encabezados, tablas, figuras, párrafos). `memoria/generate.js` no
redacta nada: aplica el formato que exige la Escuela —tipografía, interlineado,
numeración, tabla de contenidos— y compone ese texto en el `.docx` final, del
mismo modo que LaTeX compila un `.tex` a PDF sin escribir el contenido por ti.
Separar texto y formato permite además revisar los cambios de la memoria con
`git diff`, como el resto del código.

```powershell
cd memoria
npm install docx
node generate.js
```

El guion avisa de cuántas marcas de pendiente quedan en el documento.

## Estado

Fase experimental cerrada. Memoria completa a falta de revisión, formato de la
escuela y verificación de una referencia bibliográfica.
