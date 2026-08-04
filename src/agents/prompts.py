"""
Fragmentos de prompt compartidos por el sistema completo y el arnes aislado.

Viven aparte de crew.py por una razon practica: scripts/investigador_solo.py
necesita reproducir el prompt EXACTO del Investigador, pero puede ejecutarse
en un entorno donde CrewAI no esta instalado -por ejemplo el que usa AirLLM,
que exige una compilacion de PyTorch con CUDA y conviene mantener aislado del
entorno principal-. Importar crew.py arrastraria toda la pila de agentes solo
para leer dos cadenas de texto.

Manteniendolos aqui, ambos consumidores leen el MISMO literal. Si se
duplicaran, cualquier retoque en uno invalidaria en silencio la comparacion
entre motores, que es justo lo que estos fragmentos sirven para hacer posible.
"""

PROHIBICIONES = (
    "LO QUE NO EXISTE EN ESTOS DATOS, y por tanto no puedes mencionar: "
    "paises, ubicaciones, comercios, titulares, numeros de tarjeta, "
    "cuentas, historial del cliente, transacciones anteriores ni "
    "frecuencia de uso. El dataset SOLO contiene 28 componentes PCA "
    "anonimizados, un importe y una hora. Si escribes 'pais de alto "
    "riesgo' o 'historial sospechoso' estaras inventando.\n"
    "Los importes estan en EUROS, no en dolares.\n"
)

IDIOMA = (
    " Redactas SIEMPRE en castellano, incluidos titulos, etiquetas y "
    "conclusiones, sea cual sea el idioma del contexto que recibas. "
    "Los importes van en euros (EUR), nunca en dolares."
)
