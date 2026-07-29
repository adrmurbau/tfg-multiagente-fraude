# Ventana de contexto de Ollama

## El problema

Ollama usa **`num_ctx = 4096` tokens por defecto**. Cuando un prompt lo excede,
**trunca por el principio, en silencio**: sin error, sin aviso, sin ninguna
señal en la respuesta.

En este proyecto eso produjo un **falso hallazgo**. Durante un tiempo pareció
que `qwen2.5:14b` "no podía" redactar más de 18 casos y que a partir de 20 su
cobertura se volvía errática (25 % y 80 % en ejecuciones idénticas). No era una
limitación del modelo: era el punto en que el prompt cruzaba los 4096 tokens y
se perdían los primeros casos del expediente.

La pista que lo delató: el informe cubría los casos **5 a 20** y le faltaban el
**1 a 4**. Un truncamiento de salida pierde el final; uno de contexto pierde el
principio.

## Solución aplicada

`src/agents/crew.py` pasa `num_ctx=16384` al construir el LLM. Con eso caben
expedientes de 40+ casos.

## Si el parámetro no llega hasta Ollama

Algunas versiones de CrewAI o LiteLLM descartan los parámetros que no reconocen,
y la API compatible con OpenAI de Ollama **no respeta** la variable de entorno
`OLLAMA_NUM_CTX`. Si la cobertura sigue perdiendo los primeros casos, hay que
hornear el contexto en el propio modelo:

```powershell
# 1. Crear un modelo derivado con la ventana ampliada
"FROM qwen2.5:14b`nPARAMETER num_ctx 16384" | Out-File -Encoding ascii Modelfile
ollama create qwen2.5-14b-ctx16k -f Modelfile

# 2. Usarlo
python scripts\run_departamento.py --modelo qwen2.5-14b-ctx16k ...
```

## Coste en VRAM

Ampliar el contexto agranda la caché KV, que vive en la GPU. Órdenes de
magnitud aproximados para un modelo de 14B en Q4 (~9 GB):

| `num_ctx` | Caché KV aprox. | Total aprox. |
|---|---|---|
| 4096 | ~0,5 GB | ~9,5 GB |
| 16384 | ~2 GB | ~11 GB |
| 32768 | ~4 GB | ~13 GB |

Con 16 GB hay margen hasta 32k. Comprueba con `ollama ps` que la columna de
VRAM sigue al 100 %: si baja, parte del modelo se ha ido a RAM y la velocidad
se desploma.

## Cómo verificar que funciona

```powershell
ollama ps
```

La columna `CONTEXT` debe mostrar el valor ampliado, no 4096.
