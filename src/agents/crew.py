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
    construir_dossier_caso,
    n_casos,
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
        # Limites duros a nivel de peticion HTTP. El max_execution_time de
        # CrewAI no siempre corta: un modelo de razonamiento hibrido como
        # qwen3 puede quedarse generando cadena de pensamiento y bloquear el
        # lote entero. Aqui la peticion muere y la excepcion queda registrada
        # como fila con error, sin arrastrar el resto del experimento.
        # NOTA SOBRE LA VENTANA DE CONTEXTO
        # Ollama usa num_ctx=4096 por defecto y, al excederlo, TRUNCA POR EL
        # PRINCIPIO EN SILENCIO. Eso produjo un falso hallazgo: parecia que el
        # modelo no podia con mas de 18 casos, cuando lo que pasaba es que el
        # prompt cruzaba los 4096 tokens y se perdian los primeros.
        #
        # NO se puede corregir desde aqui: CrewAI enruta por el cliente de
        # OpenAI, que rechaza `num_ctx` con un TypeError. Hay que hornear la
        # ventana en el propio modelo con un Modelfile. Ver ollama/README.md.
        timeout=240,
        # 4096 y no menos: los modelos de razonamiento (qwen3, gpt-oss)
        # consumen parte del presupuesto en cadena de pensamiento antes de
        # emitir la respuesta. Con 2048 se quedaban sin margen y CrewAI
        # recibia una respuesta vacia que reintentaba, duplicando el tiempo.
        # El limite es igual para todos los modelos, por comparabilidad.
        max_tokens=4096,
    )


# ----------------------------------------------------------------------
# Los seis agentes
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# Instruccion de idioma
# ----------------------------------------------------------------------
# Los prompts estan en castellano, pero ningun modelo garantiza responder en
# el idioma de la pregunta. qwen2.5:14b es mayoritariamente ingles y chino, y
# con contextos largos (55 casos) revierte a ingles sin avisar.
#
# No es cosmetico: TODOS los patrones de PATRONES_PROHIBIDOS en
# src/evaluacion.py son regex en castellano. Un informe en ingles atraviesa el
# detector de invencion semantica sin activar una sola alarma. Se verifico:
# "originates from a high-risk country ... unusual in the customer's history"
# se audita como FIABLE, mientras su traduccion literal al castellano se marca
# como NO FIABLE. La deriva de idioma desactiva la auditoria en silencio.
# Ambas cadenas viven en src/agents/prompts.py, no aqui, porque
# scripts/investigador_solo.py necesita el MISMO texto literal para que la
# comparacion entre motores sea valida y debe poder leerlo sin importar
# CrewAI: el entorno que ejecuta AirLLM no lo tiene instalado. Duplicarlas
# invitaria a que las dos versiones divergieran sin que nadie lo notase.
from src.agents.prompts import IDIOMA, PROHIBICIONES  # noqa: F401,E402


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
        ) + IDIOMA,
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
        ) + IDIOMA,
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
        ) + IDIOMA,
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
        ) + IDIOMA,
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
        ) + IDIOMA,
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
        ) + IDIOMA,
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
def construir_tareas(ag: dict, modo: str, iterativo: bool = False) -> dict:
    """Construye las tareas y las devuelve nombradas.

    `iterativo=True` divide la investigacion en UNA TAREA POR CASO en lugar de
    pedirle al modelo N parrafos en una sola respuesta. Ver el docstring de
    `construir_dossier_caso` para los datos que motivan el cambio.
    """
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


    if iterativo:
        # UNA TAREA POR CASO. Prompt corto, salida corta, cobertura garantizada.
        tareas_investigar = [
            Task(
                description=(
                    f"{construir_dossier_caso(n)}\n\n"
                    f"Redacta UN SOLO parrafo de 3 a 5 frases explicando en "
                    f"lenguaje llano por que el detector considera sospechoso "
                    f"el CASO {n}. Menciona su importe y las variables de mayor "
                    f"aporte tal y como aparecen arriba.\n"
                    f"FORMATO: empieza con la linea 'CASO {n}' y debajo el "
                    f"parrafo en prosa. Sin tablas ni vinetas.\n"
                    + PROHIBICIONES + instruccion_veredicto
                ),
                expected_output=(
                    f"La linea 'CASO {n}' seguida de un parrafo explicativo en "
                    f"prosa." + salida_veredicto
                ),
                agent=ag["investigador"],
                context=[t_priorizar],
            )
            for n in range(1, n_casos() + 1)
        ]
    else:
        tareas_investigar = [Task(
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
                + PROHIBICIONES + instruccion_veredicto
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
        )]

    t_informe = Task(
        description=(
            "Datos verificados de los casos (unica fuente admisible de cifras):\n\n"
            f"{dossier}\n\n"
            f"El expediente contiene EXACTAMENTE {n_casos()} casos, numerados "
            f"del 1 al {n_casos()}.\n\n"
            "Redacta el informe final para el responsable de riesgos:\n"
            "1. Resumen ejecutivo (3 frases).\n"
            f"2. Tabla de casos priorizados con UNA FILA POR CADA UNO de los "
            f"{n_casos()} casos, sin excepcion. Columnas: caso, importe, "
            f"veredicto, accion recomendada (bloquear tarjeta / contactar con "
            f"el cliente / archivar).\n"
            "3. Una linea por caso con la explicacion del investigador.\n"
            "4. Nota de fiabilidad.\n\n"
            "REGLAS INNEGOCIABLES:\n"
            f"- La tabla debe tener las {n_casos()} filas. NO resumas, NO "
            f"escribas 'ejemplos', NO uses puntos suspensivos ni expresiones "
            f"como 'y los demas'. Un informe que omite casos es un informe "
            f"invalido: cada caso omitido es una decision sin registrar.\n"
            "- Si el informe resulta largo, esta bien. La exhaustividad importa "
            "  mas que la brevedad.\n"
            "- Redacta en CASTELLANO, incluidos titulos y encabezados de tabla.\n"
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
        context=[t_encuadre, t_datos, t_priorizar, t_evaluar, *tareas_investigar],
    )

    return {
        "encuadre": t_encuadre,
        "datos": t_datos,
        "priorizar": t_priorizar,
        "evaluar": t_evaluar,
        "investigar": tareas_investigar,   # lista: 1 tarea, o N si iterativo
        "informe": t_informe,
    }


# ----------------------------------------------------------------------
def construir_crew(modo: str = MODO_POR_DEFECTO, modelo: str = None,
                   verbose: bool = True, nucleo: bool = False,
                   iterativo: bool = False) -> Crew:
    """Ensambla el departamento.

    nucleo=True deja solo la cadena imprescindible (Modelador -> Investigador
    -> Reportero), que es la que produce el informe. Se salta el encuadre, el
    analisis de datos y la evaluacion, y con ello aproximadamente la mitad de
    las llamadas al LLM. Util para iterar sobre el diseno sin esperar una
    ejecucion completa en cada cambio.

    iterativo=True reparte la investigacion en una tarea por caso. Elimina el
    techo de cobertura del Investigador monolitico a cambio de un coste lineal
    en llamadas al LLM.
    """
    if modo not in MODOS:
        raise ValueError(f"Modo '{modo}' desconocido. Opciones: {MODOS}")

    llm = construir_llm(modelo)
    agentes = construir_agentes(llm, verbose=verbose)
    t = construir_tareas(agentes, modo, iterativo=iterativo)

    if nucleo:
        # Solo Modelador -> Investigador(es) -> Reportero
        for inv in t["investigar"]:
            inv.context = [t["priorizar"]]
        t["informe"].context = [t["priorizar"], *t["investigar"]]
        tareas = [t["priorizar"], *t["investigar"], t["informe"]]
        agentes = {
            k: v for k, v in agentes.items()
            if k in ("modelador", "investigador", "reportero")
        }
    else:
        tareas = [t["encuadre"], t["datos"], t["priorizar"], t["evaluar"],
                  *t["investigar"], t["informe"]]

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
