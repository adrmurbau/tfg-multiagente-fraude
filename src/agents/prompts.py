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

# Correccion de una premisa equivocada, no conocimiento nuevo.
#
# Con el prompt base, Qwen2.5-72B descarto los dos unicos fraudes de la cola
# -identificadores 12377 y 1885, de 1,00 y 2,22 EUR- razonando de forma
# explicita que el importe reducido los hacia inofensivos. El modelo de 14B
# hace lo mismo. En estos datos esa creencia esta invertida: el importe
# mediano de un fraude es 2,11 EUR frente a 19,99 de una transaccion
# legitima, y el 59,3 % de los fraudes no llega a 5 EUR frente al 25,1 % de
# las legitimas.
#
# ATENCION al enunciado. Decir "importe bajo indica fraude" entregaria la
# respuesta en la entrada y reproduciria el defecto de diseno que ya obligo a
# rehacer el experimento del dossier: el modelo obedeceria una etiqueta en
# lugar de razonar. Lo que se hace aqui es RETIRAR una premisa falsa, no
# instalar la contraria. Por eso el texto niega el valor exculpatorio del
# importe pequeno sin convertirlo en incriminatorio.
#
# El control del experimento es el caso 53: importe de 0,00 EUR y legitimo.
# Si tras la correccion el modelo confirma los fraudes pero sigue descartando
# el 53, discrimina de verdad. Si confirma los tres importes pequenos, lo
# unico que ha hecho es invertir el sesgo.
DOMINIO = (
    "\nCONTEXTO DEL DOMINIO: en fraude con tarjeta es habitual que el "
    "defraudador pruebe primero la tarjeta con un cargo de importe minimo, a "
    "veces de cero, y solo despues realice el cargo grande. Un importe "
    "reducido NO es por si mismo prueba de legitimidad, y no debe usarse como "
    "unica razon para descartar un caso. Valora los aportes de las variables.\n"
)

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
