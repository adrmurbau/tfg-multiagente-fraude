"""
El departamento de analistas - Fase 3.

Seis agentes LLM locales que analizan un lote de transacciones apoyandose en el
detector de la Fase 2. Los agentes NO se entrenan: son modelos preentrenados
que razonan, delegan y usan herramientas.

DECISIONES DE DISENO, y por que
-------------------------------

1. Proceso SECUENCIAL, no jerarquico.
   CrewAI ofrece un modo jerarquico donde un agente gestor decide a quien
   delegar en cada momento. Sobre la mesa suena mejor, pero exige del modelo
   una fiabilidad en tool calling que un 8B local no tiene: en la practica
   entra en bucles de delegacion y agota el limite de iteraciones. Con un
   flujo secuencial explicito el orden lo fija el codigo y el LLM se dedica a
   lo que sabe hacer, que es razonar sobre el contenido.

2. allow_delegation=False en todos los agentes.
   Por el mismo motivo. La delegacion entre pares multiplica las llamadas y
   las oportunidades de que el modelo genere un JSON invalido.

3. Cada agente recibe SOLO las herramientas de su rol.
   Un catalogo corto reduce drasticamente la probabilidad de que el modelo
   invoque la herramienta equivocada.

4. Los objetivos estan redactados en imperativo y con formato de salida
   explicito. Los modelos pequenos obedecen instrucciones concretas mucho
   mejor que descripciones abstractas de rol.
"""

from crewai import LLM, Agent, Crew, Process, Task

from src.agents.tools import (
    EstadisticasLoteTool,
    ExplicarTransaccionTool,
    PriorizarSospechosasTool,
    RendimientoDetectorTool,
    construir_dossier,
)
from src.config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    MODO_POR_DEFECTO,
    MODOS,
    OLLAMA_HOST,
)


def construir_llm(modelo: str = None) -> LLM:
    """Conecta CrewAI con el modelo local servido por Ollama.

    Cambiar de llama3.1:8b a qwen2.5:14b es solo cambiar LLM_MODEL en config.
    """
    return LLM(
        model=f"ollama/{modelo or LLM_MODEL}",
        base_url=OLLAMA_HOST,
        temperature=LLM_TEMPERATURE,
    )


# ----------------------------------------------------------------------
# Los seis agentes
# ----------------------------------------------------------------------
def construir_agentes(llm: LLM, verbose: bool = True) -> dict:
    # max_iter bajo y max_execution_time acotado: si el modelo se enreda
    # formateando una llamada a herramienta, preferimos que falle pronto y de
    # forma visible antes que dejarlo reintentando en silencio. Sin este
    # limite, CrewAI reintenta indefinidamente.
    comun = dict(
        llm=llm,
        allow_delegation=False,
        verbose=verbose,
        max_iter=3,
        max_execution_time=180,   # segundos por agente
    )

    coordinador = Agent(
        role="Coordinador del departamento antifraude",
        goal=(
            "Encuadrar el analisis del lote: cuantas transacciones hay, cuanto "
            "dinero esta en juego y que volumen de casos exige revision manual."
        ),
        backstory=(
            "Diriges un equipo de analistas en un banco. No revisas casos uno a "
            "uno: tu trabajo es dimensionar el problema y decidir donde poner la "
            "atencion del equipo, que siempre es un recurso escaso."
        ),
        tools=[EstadisticasLoteTool()],
        **comun,
    )

    analista_datos = Agent(
        role="Analista de datos",
        goal=(
            "Describir la composicion del lote y senalar que patrones de importe "
            "y de hora merecen atencion."
        ),
        backstory=(
            "Llevas anos mirando datos transaccionales. Sabes que en este dataset "
            "las variables V1 a V28 son componentes PCA anonimizados y por tanto "
            "no tienen significado de negocio directo; solo el importe y la hora "
            "son interpretables por un humano. No finges entender lo que no se "
            "puede entender."
        ),
        tools=[EstadisticasLoteTool(), PriorizarSospechosasTool()],
        **comun,
    )

    modelador = Agent(
        role="Modelador de riesgo",
        goal=(
            "Presentar con exactitud los casos que el detector ha elevado a "
            "revision, con su identificador, probabilidad e importe."
        ),
        backstory=(
            "Eres el responsable del modelo de deteccion. Conoces sus tripas: un "
            "XGBoost supervisado entrenado con particion temporal, acompanado de "
            "un Isolation Forest no supervisado. Nunca inventas puntuaciones: "
            "siempre las consultas a la herramienta."
        ),
        tools=[PriorizarSospechosasTool()],
        **comun,
    )

    evaluador = Agent(
        role="Evaluador de calidad del modelo",
        goal=(
            "Explicar cuanta confianza merece el detector y que tasa de falsos "
            "positivos debe esperar el equipo al revisar los casos."
        ),
        backstory=(
            "Tu obsesion son los falsos positivos: cada uno cuesta tiempo de "
            "analista y molesta a un cliente inocente. Pero tambien vigilas los "
            "falsos negativos, que son fraude que se escapa. Sabes que con un "
            "0,17 % de fraude la exactitud no significa nada y que la metrica "
            "honesta es el AUC-PR."
        ),
        tools=[RendimientoDetectorTool()],
        **comun,
    )

    investigador = Agent(
        role="Investigador de casos sospechosos",
        goal=(
            "Explicar, caso por caso y en lenguaje comprensible para alguien sin "
            "formacion tecnica, por que el detector considera sospechosa cada "
            "transaccion."
        ),
        backstory=(
            "Eres quien traduce el modelo a lenguaje humano. Para cada caso "
            "consultas la descomposicion por variables y explicas que empuja la "
            "decision hacia fraude y que la frena. Como V1 a V28 son componentes "
            "anonimizados, describes su efecto ('un valor muy atipico en V14') "
            "sin atribuirles un significado de negocio que no tienen. Senalas "
            "los importes pequenos, porque las tarjetas robadas suelen probarse "
            "con micropagos antes del cargo grande."
        ),
        # SIN herramientas, deliberadamente. El expediente completo ya viaja
        # en su prompt, asi que la herramienta solo le anadia la tentacion de
        # copiar su salida tabulada en lugar de redactar. Quitandosela, la
        # unica respuesta posible es la prosa que se le pide. Ademas ahorra
        # cuatro llamadas al LLM por ejecucion.
        tools=[],
        **comun,
    )

    reportero = Agent(
        role="Redactor de informes de fraude",
        goal=(
            "Redactar el informe final priorizado, con semaforo de riesgo y una "
            "recomendacion accionable por caso."
        ),
        backstory=(
            "Escribes para el responsable de riesgos, que tiene cinco minutos y "
            "no es tecnico. Vas al grano, ordenas por gravedad y cada caso lleva "
            "una accion concreta: bloquear la tarjeta, llamar al cliente o "
            "archivar. No repites el analisis: lo sintetizas."
        ),
        tools=[],
        **comun,
    )

    return {
        "coordinador": coordinador,
        "analista_datos": analista_datos,
        "modelador": modelador,
        "evaluador": evaluador,
        "investigador": investigador,
        "reportero": reportero,
    }


# ----------------------------------------------------------------------
# Las tareas
# ----------------------------------------------------------------------
def construir_tareas(ag: dict, modo: str) -> list:
    t_encuadre = Task(
        description=(
            "Consulta las estadisticas del lote con la herramienta disponible. "
            "Resume en 3 o 4 frases: cuantas transacciones hay, cuantas de riesgo "
            "alto, el importe total y el importe en riesgo."
        ),
        expected_output=(
            "Un parrafo breve con las cifras clave del lote. Nada de listas."
        ),
        agent=ag["coordinador"],
    )

    t_datos = Task(
        description=(
            "Describe la composicion del lote. Comenta el reparto de importes y "
            "la franja horaria. Si observas que las transacciones de riesgo alto "
            "tienen importes llamativamente bajos, dilo explicitamente. "
            "Recuerda: V1 a V28 son componentes PCA sin significado de negocio."
        ),
        expected_output=(
            "De 4 a 6 frases sobre la composicion del lote, mencionando importes "
            "y horas. Sin inventar interpretaciones de las variables V. "
            "PROSA CONTINUA: no reproduzcas la salida de la herramienta ni "
            "generes tablas ni listas."
        ),
        agent=ag["analista_datos"],
        context=[t_encuadre],
    )

    # El expediente se calcula sin LLM y se inyecta literalmente en el prompt.
    # Asi los identificadores y las cifras no dependen de que un modelo de 8B
    # se acuerde de copiarlos en su respuesta.
    dossier = construir_dossier()

    t_priorizar = Task(
        description=(
            "Este es el expediente de casos que el detector ha elevado a "
            "revision:\n\n"
            f"{dossier}\n\n"
            "Reproduce una tabla con una fila por caso, con las columnas "
            "id, probabilidad, riesgo e importe. Copia las cifras TAL CUAL "
            "aparecen arriba. No anadas casos que no esten en el expediente."
        ),
        expected_output=(
            "Una tabla con una fila por cada caso del expediente, con id, "
            "probabilidad, riesgo e importe exactos."
        ),
        agent=ag["modelador"],
        context=[t_encuadre],
    )

    t_evaluar = Task(
        description=(
            "Consulta las metricas de validacion del detector. Explica en "
            "lenguaje llano cuanto puede fiarse el equipo de las puntuaciones "
            "altas, y advierte de la tasa de falsos positivos que cabe esperar "
            "al bajar por el ranking."
        ),
        expected_output=(
            "De 4 a 6 frases sobre la fiabilidad del detector, citando AUC-PR y "
            "precision@N, y una advertencia sobre falsos positivos. "
            "PROSA CONTINUA: cita las cifras dentro de tus frases, no copies el "
            "bloque que devuelve la herramienta."
        ),
        agent=ag["evaluador"],
        context=[t_priorizar],
    )

    # --- La tarea que cambia entre modos ---
    if modo == "revisa":
        instruccion_veredicto = (
            "Para CADA caso emite ademas un veredicto: CONFIRMADO si las "
            "evidencias respaldan la sospecha, o DESCARTADO si crees que es un "
            "falso positivo. Se conservador: descartar un fraude real es mucho "
            "mas caro que revisar de mas. Escribe el veredicto en MAYUSCULAS al "
            "final de cada caso, en una linea aparte."
        )
        salida_veredicto = " Cada caso termina con una linea 'VEREDICTO: CONFIRMADO' o 'VEREDICTO: DESCARTADO'."
    else:
        instruccion_veredicto = (
            "NO emitas juicio sobre si el caso es o no fraude: esa decision es "
            "del detector. Tu trabajo es exclusivamente explicar su razonamiento."
        )
        salida_veredicto = ""

    t_investigar = Task(
        description=(
            "Este es el expediente completo, con la descomposicion por "
            "variables de cada caso:\n\n"
            f"{dossier}\n\n"
            "Redacta un parrafo por CADA caso del expediente, explicando en "
            "lenguaje llano por que el detector lo considera sospechoso. "
            "Menciona su importe real y las variables de mayor aporte tal y "
            "como aparecen arriba.\n"
            "FORMATO OBLIGATORIO: para cada caso, una linea 'CASO <id>' y "
            "debajo un parrafo de 3 a 5 frases en prosa. PROHIBIDO responder "
            "con tablas, listas o vinetas: el resultado debe ser texto "
            "corrido.\n\n"
            "LO QUE NO EXISTE EN ESTOS DATOS, y por tanto no puedes mencionar: "
            "paises, ubicaciones, comercios, titulares, numeros de tarjeta, "
            "cuentas, historial del cliente, transacciones anteriores ni "
            "frecuencia de uso. El dataset SOLO contiene 28 componentes PCA "
            "anonimizados, un importe y una hora. Si escribes 'pais de alto "
            "riesgo' o 'historial sospechoso' estaras inventando.\n"
            "Los importes estan en EUROS, no en dolares.\n"
            + instruccion_veredicto
        ),
        expected_output=(
            "Un bloque por transaccion, encabezado por su identificador, con la "
            "explicacion en lenguaje natural. Cada bloque debe ser PROSA "
            "explicativa escrita por ti: la salida de la herramienta es tu "
            "materia prima, no tu respuesta. Un lector no tecnico tiene que "
            "entenderlo sin ver ninguna tabla." + salida_veredicto
        ),
        agent=ag["investigador"],
        context=[t_priorizar, t_evaluar],
    )

    t_informe = Task(
        description=(
            "Datos verificados de los casos (unica fuente admisible de cifras):\n\n"
            f"{dossier}\n\n"
            "Redacta el informe final para el responsable de riesgos:\n"
            "1. Resumen ejecutivo (3 frases).\n"
            "2. Tabla de casos priorizados con semaforo: ALTO=rojo, "
            "MEDIO=ambar, BAJO=verde.\n"
            "3. Un apartado por caso con la explicacion del investigador y una "
            "accion recomendada (bloquear tarjeta / contactar con el cliente / "
            "archivar).\n"
            "4. Nota de fiabilidad.\n\n"
            "REGLAS INNEGOCIABLES:\n"
            "- Las explicaciones deben salir del analisis del investigador. Si "
            "  no dispones de explicacion para un caso, escribe 'Sin analisis "
            "  disponible'. NUNCA te la inventes.\n"
            "- No menciones paises, comercios, cuentas, titulares ni historial "
            "  de cliente: esos datos NO existen en este dataset.\n"
            "- No sumes ni calcules importes: si citas un total, copialo del "
            "  expediente.\n"
            + ("- El investigador ha emitido un VEREDICTO por caso. Los "
               "  CONFIRMADOS van en la tabla principal. Los DESCARTADOS van "
               "  en una seccion aparte titulada 'Casos descartados en "
               "  revision', indicando el motivo. No los elimines del informe: "
               "  un descarte tambien es una decision que debe quedar "
               "  registrada y ser auditable.\n"
               if modo == "revisa" else "")
            + "Escribe en Markdown."
        ),
        expected_output=(
            "Un informe en Markdown con resumen ejecutivo, tabla priorizada, "
            "casos con accion recomendada y nota de fiabilidad."
        ),
        agent=ag["reportero"],
        context=[t_encuadre, t_datos, t_priorizar, t_evaluar, t_investigar],
    )

    return [t_encuadre, t_datos, t_priorizar, t_evaluar, t_investigar, t_informe]


# ----------------------------------------------------------------------
def construir_crew(modo: str = MODO_POR_DEFECTO, modelo: str = None,
                   verbose: bool = True, nucleo: bool = False) -> Crew:
    """Ensambla el departamento.

    nucleo=True deja solo la cadena imprescindible (Modelador -> Investigador
    -> Reportero), que es la que produce el informe. Se salta el encuadre, el
    analisis de datos y la evaluacion, y con ello aproximadamente la mitad de
    las llamadas al LLM. Util para iterar sobre el diseno sin esperar una
    ejecucion completa en cada cambio.
    """
    if modo not in MODOS:
        raise ValueError(f"Modo '{modo}' desconocido. Opciones: {MODOS}")

    llm = construir_llm(modelo)
    agentes = construir_agentes(llm, verbose=verbose)
    tareas = construir_tareas(agentes, modo)

    if nucleo:
        # Indices 2, 4 y 5 = priorizar, investigar, informe
        tareas = [tareas[2], tareas[4], tareas[5]]
        # Reconstruir el contexto: las tareas suprimidas ya no existen
        tareas[1].context = [tareas[0]]
        tareas[2].context = [tareas[0], tareas[1]]
        agentes = {
            k: v for k, v in agentes.items()
            if k in ("modelador", "investigador", "reportero")
        }

    return Crew(
        agents=list(agentes.values()),
        tasks=tareas,
        process=Process.sequential,
        verbose=verbose,
        # Sin telemetria. CrewAI ofrece enviar trazas de ejecucion a
        # app.crewai.com, lo que incluiria prompts, respuestas del LLM y
        # salidas de las herramientas: es decir, datos de transacciones
        # saliendo de la maquina. El TFG sostiene que el sistema es
        # enteramente local, asi que esto queda desactivado por diseno.
        tracing=False,
    )
