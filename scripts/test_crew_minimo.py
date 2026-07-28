"""
Prueba minima de CrewAI + Ollama: UN agente, UNA herramienta, UNA tarea.

El paso mas pequeno que demuestra que las dos capas se entienden. Si esto
falla, no tiene sentido lanzar seis agentes: el problema esta en la conexion
con el LLM o en el tool calling del modelo, no en el diseno del departamento.

Es tambien la prueba que decide si llama3.1:8b sirve o hay que subir a
qwen2.5:14b, porque lo que aqui se pone a prueba es exactamente su punto
debil: invocar una herramienta con argumentos bien formados.

Uso:
    python scripts/test_crew_minimo.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task  # noqa: E402

from src.agents.crew import construir_llm  # noqa: E402
from src.agents.tools import (  # noqa: E402
    PriorizarSospechosasTool,
    inicializar_contexto,
)
from src.config import LLM_MODEL, TARGET_COL  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import construir_lote  # noqa: E402

print("=" * 66)
print("  PRUEBA MINIMA: CrewAI + Ollama + 1 herramienta")
print("=" * 66)

print("\n[1/4] Preparando el lote...")
lote = construir_lote(cargar_dataset(), n=200, n_fraudes=3)
inicializar_contexto(lote)
print(f"      {len(lote)} transacciones, "
      f"{int(lote[TARGET_COL].sum())} fraudes ocultos")

print(f"\n[2/4] Conectando con {LLM_MODEL} via Ollama...")
llm = construir_llm()

print("\n[3/4] Montando un agente con una sola herramienta...")
analista = Agent(
    role="Analista de fraude",
    goal="Identificar las transacciones mas sospechosas de un lote.",
    backstory=(
        "Trabajas en el departamento antifraude de un banco. Dispones de un "
        "detector automatico al que puedes consultar. Nunca inventas cifras: "
        "siempre las consultas a la herramienta."
    ),
    tools=[PriorizarSospechosasTool()],
    llm=llm,
    allow_delegation=False,
    verbose=True,
    max_iter=5,
)

tarea = Task(
    description=(
        "Obten las 3 transacciones mas sospechosas del lote usando la "
        "herramienta disponible. Despues resume en dos frases que has "
        "encontrado, citando sus identificadores y sus importes."
    ),
    expected_output=(
        "La tabla devuelta por la herramienta y dos frases de resumen "
        "mencionando identificadores e importes."
    ),
    agent=analista,
)

print("\n[4/4] Ejecutando (esto tarda; el modelo corre en local)...\n")
t0 = time.perf_counter()
try:
    resultado = Crew(
        agents=[analista], tasks=[tarea],
        process=Process.sequential, verbose=True,
        tracing=False,   # nada sale de esta maquina
    ).kickoff()
    dt = time.perf_counter() - t0

    print("\n" + "=" * 66)
    print("  RESULTADO")
    print("=" * 66)
    print(resultado)
    print(f"\n  Tiempo total: {dt:.1f}s")

    texto = str(resultado)
    reales = [str(i) for i in lote.nlargest(3, "Amount").index]  # referencia debil
    print("\n  Comprobacion rapida:")
    print(f"    ¿Menciona identificadores numericos?  "
          f"{'si' if any(c.isdigit() for c in texto) else 'NO'}")
    print(f"    Longitud de la respuesta: {len(texto)} caracteres")
    print("\n  [OK]  CrewAI y Ollama se entienden. Adelante con los 6 agentes.")

except Exception as e:
    print(f"\n  [FALLO]  {type(e).__name__}: {e}")
    print("\n  Diagnostico habitual:")
    print("    - 'connection refused'  -> Ollama no esta corriendo: ollama serve")
    print("    - errores de tool call  -> el 8B no formatea bien los argumentos.")
    print("                               Prueba qwen2.5:14b:")
    print("                                 ollama pull qwen2.5:14b")
    print("                                 y cambia LLM_MODEL en src/config.py")
    sys.exit(1)
