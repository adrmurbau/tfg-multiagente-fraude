"""
Evaluacion y auditoria del sistema multi-agente.

Unica fuente de verdad para medir una ejecucion. La usan tanto
run_departamento.py (que produce texto legible) como experimento.py (que
produce numeros agregables), de modo que las tablas de la memoria y los
informes individuales no puedan contradecirse.

Devuelve SIEMPRE estructuras de datos, nunca texto formateado: el formato es
responsabilidad de quien llama.
"""

import re

from src.config import TARGET_COL

# ----------------------------------------------------------------------
# Extraccion de informacion del texto generado por los agentes
# ----------------------------------------------------------------------

# Identificadores SOLO en contextos donde de verdad se cita una transaccion.
# La version anterior cogia cualquier numero suelto y marcaba como id ajeno
# el '4' de "se han identificado 4 casos". Buscar el numero en su contexto es
# mucho mas fiable que buscar el numero solo.
_PATRONES_ID = [
    r"CASO\s+#?(\d{1,6})",              # 'CASO 156'
    r"[Tt]ransacci[óo]n\s+#?(\d{1,6})",  # 'Transacción 0'
    r"\bid\s*[:=]?\s*(\d{1,6})\b",       # 'id: 156'
    r"^\s*\|\s*\*{0,2}(\d{1,6})\*{0,2}\s*\|",  # celda de tabla Markdown
]
_RE_IDS = [re.compile(p, re.MULTILINE) for p in _PATRONES_ID]

# Un termino prohibido dentro de una negacion no es una invencion. Los modelos
# suelen cerrar el informe declarando que han cumplido la norma ("sin
# mencionar paises, comercios ni historial de cliente"), y esa frase citaba
# los terminos vetados y hacia saltar la alarma sobre un informe correcto.
_RE_NEGACION = re.compile(
    # 'sin acceso a historial', 'sin mencionar paises'
    r"(sin\s+(acceso|informaci[óo]n|datos|mencionar|citar|incluir|considerar|"
    r"referencias?|hacer|conocer|disponer|atender|recurrir|apelar)|"
    # 'la falta de informacion sobre el historial'
    r"(falta|ausencia|carencia)\s+de|carece[nr]?\s+de|"
    # 'no se dispone de historial', 'no hay comercio'
    r"no\s+(se\s+)?(dispone|dispongo|disponemos|tiene|tenemos|cuenta\s+con|"
    r"menciona|incluye|cita|hay|existen?|contiene|consta)|"
    # enumeraciones negativas: 'ni historial de cliente'
    r"ning[úu]n[ao]?|tampoco|ni\s)",
    re.IGNORECASE,
)
VENTANA_NEGACION = 120  # caracteres antes del termino donde buscar la negacion

# Bloque 'CASO <id> ... VEREDICTO: <X>'. Non-greedy para no tragarse el
# siguiente caso.
_RE_VEREDICTO = re.compile(
    r"CASO\s+(\d+)(.*?)VEREDICTO:\s*(CONFIRMADO|DESCARTADO)",
    re.DOTALL | re.IGNORECASE,
)

# Conceptos que NO existen en el dataset ULB: solo hay 28 componentes PCA
# anonimizados, un importe y una hora. Los patrones son especificos a
# proposito; una version anterior buscaba la palabra 'cuenta' suelta y
# marcaba como alucinacion la locucion 'tener en cuenta'.
PATRONES_PROHIBIDOS = [
    (r"\bpa[ií]s(es)?\b", "el dataset no contiene informacion geografica"),
    (r"\bubicaci[óo]n|\bgeolocalizaci[óo]n", "no hay datos de localizacion"),
    (r"\bcomercio|\bestablecimiento|\bcomerciante", "no se identifica el comercio"),
    # 'titular' a secas NO es invencion: una de las acciones recomendadas es
    # "contactar con el cliente", asi que referirse al titular de la tarjeta
    # es inevitable. Solo es invencion si afirma tener DATOS suyos.
    (r"(datos|nombre|edad|direcci[óo]n|perfil|dni) del titular|"
     r"titular\s+(se\s+llama|es\s+un|reside|vive)",
     "no hay datos identificativos del titular"),
    (r"n[úu]mero de (cuenta|tarjeta)|cuenta (bancaria|del cliente)",
     "no hay identificador de cuenta ni de tarjeta"),
    (r"historial (de[l]? )?(cliente|actividad|transacciones|compras)",
     "no hay historial: cada fila es independiente"),
    (r"transacciones (anteriores|previas|recientes)",
     "no hay relacion entre transacciones"),
    (r"corto per[íi]odo|pocos minutos|en cuesti[óo]n de (minutos|segundos)",
     "no se calcula frecuencia entre transacciones"),
]


def ids_citados(texto: str) -> set:
    """Identificadores de transaccion citados en el informe.

    Solo cuenta numeros que aparecen en contextos de identificacion ('CASO
    156', 'Transacción 0', celda de tabla), no cualquier cifra del texto.
    """
    ids = set()
    for rx in _RE_IDS:
        ids.update(int(m) for m in rx.findall(texto))
    return ids


def _en_negacion(texto: str, pos: int) -> bool:
    """¿El termino en esa posicion esta dentro de una frase negativa?"""
    inicio = max(0, pos - VENTANA_NEGACION)
    return bool(_RE_NEGACION.search(texto[inicio:pos]))


def veredictos_por_caso(texto: str) -> dict:
    """Mapea cada caso a su veredicto: {156: 'CONFIRMADO', 352: 'DESCARTADO'}.

    Cuenta cuantos, pero sobre todo CUALES. Saber que se descartaron dos casos
    no dice nada; saber que uno de ellos era fraude real lo dice todo.
    """
    return {
        int(idx): veredicto.upper()
        for idx, _, veredicto in _RE_VEREDICTO.findall(texto)
    }


# ----------------------------------------------------------------------
# Auditoria de fiabilidad
# ----------------------------------------------------------------------
def auditar(informe: str, ids_expediente, ids_lote) -> dict:
    """Comprueba que el informe habla de cosas que existen.

    Dos niveles, porque el primero no basta: en una ejecucion real el sistema
    cito los cuatro identificadores correctos y aun asi el informe era falso,
    porque atribuia a las transacciones un 'pais de alto riesgo' inexistente.
    """
    citados = ids_citados(informe)
    validos, universo = set(ids_expediente), set(int(i) for i in ids_lote)

    inventados = sorted(citados - universo)
    fuera = sorted((citados & universo) - validos)
    cubiertos = sorted(validos & citados)

    bajo = informe.lower()
    conceptos = []
    for patron, motivo in PATRONES_PROHIBIDOS:
        # Solo cuenta si ALGUNA aparicion esta fuera de una negacion
        afirmativas = [m for m in re.finditer(patron, bajo)
                       if not _en_negacion(bajo, m.start())]
        if afirmativas:
            conceptos.append((afirmativas[0].group(0), motivo))

    if inventados:
        veredicto = "NO FIABLE - identificadores inventados"
    elif conceptos:
        veredicto = "NO FIABLE - invencion semantica"
    elif len(cubiertos) < len(validos):
        veredicto = "INCOMPLETO"
    else:
        veredicto = "FIABLE"

    return {
        "veredicto": veredicto,
        "fiable": veredicto == "FIABLE",
        "ids_inventados": inventados,
        "ids_fuera_expediente": fuera,
        "ids_cubiertos": cubiertos,
        "cobertura": len(cubiertos) / max(len(validos), 1),
        "conceptos_inventados": conceptos,
        "menciona_dolares": "$" in informe or "dolar" in bajo,
    }


# ----------------------------------------------------------------------
# Metricas del sistema completo
# ----------------------------------------------------------------------
def medir_sistema(lote, detector, salida_investigador: str = "",
                  modo: str = "interpreta") -> dict:
    """Contrasta lo que hizo el sistema con las etiquetas reales.

    Distingue tres niveles, y la distincion es el nucleo del experimento:

      recall_detector : que fraude eleva la capa 1. Techo del sistema.
      recall_sistema  : que fraude sobrevive a la capa 2. En modo
                        'interpreta' coincide con el anterior; en modo
                        'revisa' puede ser menor, nunca mayor.
      fraude_descartado : el dano concreto que hace el LLM al decidir.
    """
    expediente = detector.seleccionar_casos(lote)
    ids_exp = list(expediente.index)

    fraudes_totales = int(lote[TARGET_COL].sum())
    fraudes_elevados = int(expediente[TARGET_COL].sum())

    veredictos = veredictos_por_caso(salida_investigador) if modo == "revisa" else {}
    descartados = {i for i, v in veredictos.items() if v == "DESCARTADO"}

    # Descartes que eran fraude real: el error caro
    fraude_descartado = sorted(
        i for i in descartados
        if i in lote.index and lote.loc[i, TARGET_COL] == 1
    )
    # Descartes acertados: falsos positivos que el LLM filtro bien
    descarte_correcto = sorted(
        i for i in descartados
        if i in lote.index and lote.loc[i, TARGET_COL] == 0
    )

    elevados_finales = len(ids_exp) - len(descartados)
    fraude_final = fraudes_elevados - len(fraude_descartado)

    return {
        "n_lote": len(lote),
        "fraudes_totales": fraudes_totales,
        "casos_elevados": len(ids_exp),
        "ids_expediente": ids_exp,
        "fraudes_elevados": fraudes_elevados,
        "recall_detector": fraudes_elevados / max(fraudes_totales, 1),
        "precision_detector": fraudes_elevados / max(len(ids_exp), 1),
        "n_confirmados": sum(1 for v in veredictos.values() if v == "CONFIRMADO"),
        "n_descartados": len(descartados),
        "fraude_descartado": fraude_descartado,
        "n_fraude_descartado": len(fraude_descartado),
        "descarte_correcto": descarte_correcto,
        "n_descarte_correcto": len(descarte_correcto),
        "recall_sistema": fraude_final / max(fraudes_totales, 1),
        "precision_sistema": fraude_final / max(elevados_finales, 1),
        "falsos_negativos_detector": sorted(
            int(i) for i in lote.index
            if lote.loc[i, TARGET_COL] == 1 and i not in ids_exp
        ),
    }
