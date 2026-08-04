"""
Herramientas de CrewAI - el puente entre las dos capas.

Cada herramienta expone una capacidad del detector (capa 1) en un formato que
un LLM (capa 2) pueda invocar y, sobre todo, leer. El diseno persigue tres
cosas, porque un modelo de 8B es bastante mas fragil que GPT-4:

  1. Firmas minimas. Cuantos menos argumentos, menos ocasiones de que el
     modelo alucine un JSON invalido.
  2. Salidas en texto plano, no en JSON. El LLM tiene que razonar sobre el
     resultado, no parsearlo.
  3. Fallo explicito y en lenguaje natural. Si el agente se equivoca de
     indice, el mensaje de error le dice como corregirse.

El estado compartido (detector y lote en curso) vive en un contexto de modulo:
las herramientas de CrewAI se instancian sueltas y no reciben dependencias.
"""

from typing import Type

import pandas as pd
try:
    from crewai.tools import BaseTool
except ModuleNotFoundError:
    # Este modulo contiene dos cosas distintas: la construccion del expediente
    # -logica del dominio, en Python plano- y cuatro envoltorios de CrewAI que
    # la exponen como herramientas a los agentes.
    #
    # scripts/investigador_solo.py necesita lo primero y no lo segundo, y en el
    # entorno de AirLLM CrewAI no esta instalado: instalarlo arrastraria su
    # propia version fijada de PyTorch y podria sustituir la compilacion con
    # CUDA que ese entorno existe para tener.
    #
    # El sustituto permite DEFINIR las clases pero no instanciarlas, de modo
    # que si algun dia falta CrewAI donde si hace falta, el fallo sea inmediato
    # y explicito en lugar de una degradacion silenciosa.
    class BaseTool:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "CrewAI no esta instalado en este entorno. Las funciones de "
                "expediente de src/agents/tools.py si funcionan sin el; las "
                "herramientas de agente, no."
            )
from pydantic import BaseModel, Field

from src.config import TOP_N
from src.detector.predict import DetectorFraude


# ----------------------------------------------------------------------
# Niveles de informacion del expediente
# ----------------------------------------------------------------------
# Un experimento en modo `revisa` con umbral permisivo dio un resultado que
# invitaba a concluir que el modelo redescubria, razonando sobre las
# contribuciones SHAP, la frontera de confianza del detector. No era cierto:
# el expediente incluye la linea "Nivel de riesgo", calculada con el corte
# 0,80, y los descartes cuadraban exactamente con esa etiqueta. En 3 de 4
# turnos el modelo descarto justo los casos no marcados como ALTO.
#
# El diseno del expediente entregaba la respuesta en la entrada, de modo que
# el experimento no distinguia entre RAZONAR y OBEDECER una etiqueta. Estos
# tres niveles permiten separarlo mediante ablacion:
#
#   completo  : probabilidad + nivel de riesgo + contribuciones  (original)
#   sin_nivel : probabilidad + contribuciones                    (sin la etiqueta)
#   ciego     : solo contribuciones, importe y hora              (sin puntuacion)
#
# Si la discriminacion se mantiene en `ciego`, el modelo razona sobre la
# evidencia. Si se pierde, no aporta criterio propio. Ambos resultados son
# publicables.
NIVELES_DOSSIER = ("completo", "sin_nivel", "ciego")


# ----------------------------------------------------------------------
# Contexto compartido
# ----------------------------------------------------------------------
class _Contexto:
    """Detector y lote activos. Se inicializa una vez por ejecucion."""

    def __init__(self):
        self.detector: DetectorFraude | None = None
        self.lote: pd.DataFrame | None = None
        self.puntuado: pd.DataFrame | None = None
        self.capacidad: int | None = None   # casos que el equipo puede revisar
        self.umbral: float | None = None    # corte de probabilidad (None = ALTO)
        self.dossier: str = "completo"      # ver NIVELES_DOSSIER
        # Sustituye a CASOS_MIN. En operacion continua debe valer 0: ver el
        # docstring de DetectorFraude.seleccionar_casos. Debe viajar en el
        # contexto, porque si no el crew recibe un expediente distinto del
        # que cuenta quien lo invoca.
        self.minimo: int | None = None
        # Correspondencia numero de caso (1..N) -> indice real del DataFrame.
        # Ver `construir_dossier` para el porque.
        self.mapa: dict[int, int] = {}

    def inicializar(self, lote: pd.DataFrame, detector: DetectorFraude = None,
                    capacidad: int = None, umbral: float = None,
                    dossier: str = "completo", minimo: int = None):
        if dossier not in NIVELES_DOSSIER:
            raise ValueError(f"dossier debe ser uno de {NIVELES_DOSSIER}, no {dossier!r}")
        self.detector = detector or DetectorFraude()
        self.lote = lote
        self.capacidad = capacidad
        self.umbral = umbral
        self.dossier = dossier
        self.minimo = minimo
        casos = (detector or self.detector).seleccionar_casos(
            lote, capacidad, umbral, minimo)
        self.mapa = {n: int(idx) for n, idx in enumerate(casos.index, start=1)}
        # Se puntua una sola vez: los agentes consultaran muchas veces y no
        # tiene sentido reevaluar el modelo en cada llamada.
        self.puntuado = self.detector.puntuar(lote)
        return self

    def exigir(self):
        if self.puntuado is None:
            raise RuntimeError(
                "Contexto sin inicializar. Llama a inicializar_contexto(lote) "
                "antes de arrancar el crew."
            )


CTX = _Contexto()


def inicializar_contexto(lote: pd.DataFrame, detector: DetectorFraude = None,
                         capacidad: int = None, umbral: float = None,
                         dossier: str = "completo", minimo: int = None):
    """Prepara el lote que analizara el departamento.

    `capacidad` = cuantos casos puede revisar el equipo en ese turno.
    """
    return CTX.inicializar(lote, detector, capacidad, umbral, dossier, minimo)


# ----------------------------------------------------------------------
# 1. Estadisticas del lote  (Analista de datos)
# ----------------------------------------------------------------------
class EstadisticasLoteTool(BaseTool):
    name: str = "estadisticas_del_lote"
    description: str = (
        "Devuelve un resumen estadistico del lote de transacciones bajo analisis: "
        "cuantas hay, como se reparten por nivel de riesgo, importes implicados y "
        "rango horario. No necesita argumentos. Usala SIEMPRE al principio para "
        "saber a que te enfrentas."
    )

    def _run(self) -> str:
        CTX.exigir()
        p = CTX.puntuado
        base = [f"LOTE BAJO ANALISIS", f"  Transacciones            : {len(p):,}"]

        # El reparto por semaforo revela el corte 0,80. Se omite cuando el
        # experimento oculta la etiqueta, o la ablacion no serviria de nada.
        if CTX.dossier == "completo":
            conteo = p["riesgo"].value_counts()
            base += [f"  Riesgo ALTO (rojo)       : {conteo.get('ALTO', 0)}",
                     f"  Riesgo MEDIO (ambar)     : {conteo.get('MEDIO', 0)}",
                     f"  Riesgo BAJO (verde)      : {conteo.get('BAJO', 0)}"]
        if CTX.dossier in ("completo", "sin_nivel"):
            base += [f"  Probabilidad maxima      : {p['prob_fraude'].max():.4f}",
                     f"  Probabilidad media       : {p['prob_fraude'].mean():.4f}"]
        base += [
            f"  Importe total del lote   : {p['Amount'].sum():,.2f} EUR",
            f"  Importe medio            : {p['Amount'].mean():.2f} EUR",
            f"  Franja horaria           : {p['Hour'].min():.1f}h - {p['Hour'].max():.1f}h",
        ]
        return "\n".join(base)


# ----------------------------------------------------------------------
# 2. Priorizar sospechosas  (Coordinador / Modelador)
# ----------------------------------------------------------------------
class _ArgsTop(BaseModel):
    n: int = Field(
        default=10,
        description="Cuantas transacciones devolver, entre 1 y 50.",
    )


class PriorizarSospechosasTool(BaseTool):
    name: str = "priorizar_sospechosas"
    description: str = (
        "Devuelve las N transacciones mas sospechosas del lote segun el detector, "
        "ordenadas de mayor a menor riesgo, con su identificador, probabilidad, "
        "semaforo e importe. Usa el identificador que devuelve esta herramienta "
        "para pedir explicaciones detalladas."
    )
    args_schema: Type[BaseModel] = _ArgsTop

    def _run(self, n: int = 10) -> str:
        CTX.exigir()
        n = max(1, min(int(n), 50))
        top = CTX.puntuado.nlargest(n, "prob_fraude")

        # Se numeran 1..N igual que en el expediente: el LLM nunca ve indices
        # crudos del DataFrame, que corrompe cuando tienen 4-5 cifras.
        filas = [f"TOP {n} TRANSACCIONES SOSPECHOSAS", ""]
        # La herramienta respeta el nivel de informacion del expediente: si el
        # experimento oculta la etiqueta de riesgo, no puede reaparecer aqui.
        if CTX.dossier == "completo":
            filas.append(f"{'caso':>6} {'prob':>8} {'riesgo':>7} {'importe':>11} {'hora':>6}")
            filas.append("-" * 42)
            for pos, (idx, f) in enumerate(top.iterrows(), start=1):
                filas.append(f"{pos:>6} {f['prob_fraude']:>8.4f} {f['riesgo']:>7} "
                             f"{f['Amount']:>11.2f} {f['Hour']:>6.1f}")
            altos = int((top["riesgo"] == "ALTO").sum())
            filas.append("")
            filas.append(f"De estas {n}, {altos} superan el umbral de riesgo ALTO (0.80).")
        elif CTX.dossier == "sin_nivel":
            filas.append(f"{'caso':>6} {'prob':>8} {'importe':>11} {'hora':>6}")
            filas.append("-" * 34)
            for pos, (idx, f) in enumerate(top.iterrows(), start=1):
                filas.append(f"{pos:>6} {f['prob_fraude']:>8.4f} "
                             f"{f['Amount']:>11.2f} {f['Hour']:>6.1f}")
        else:
            filas.append(f"{'caso':>6} {'importe':>11} {'hora':>6}")
            filas.append("-" * 25)
            for pos, (idx, f) in enumerate(top.iterrows(), start=1):
                filas.append(f"{pos:>6} {f['Amount']:>11.2f} {f['Hour']:>6.1f}")
        return "\n".join(filas)


# ----------------------------------------------------------------------
# 3. Explicar una transaccion  (Investigador / Explicador)
# ----------------------------------------------------------------------
class _ArgsExplicar(BaseModel):
    id_transaccion: int = Field(
        description="Identificador de la transaccion, tal y como aparece en la "
                    "columna 'id' de priorizar_sospechosas.",
    )


class ExplicarTransaccionTool(BaseTool):
    name: str = "explicar_transaccion"
    description: str = (
        "Explica POR QUE el detector considera sospechosa una transaccion concreta. "
        "Descompone la decision en las variables que mas contribuyen, indicando si "
        "cada una empuja hacia FRAUDE o hacia LEGITIMA. Requiere el identificador "
        "numerico de la transaccion."
    )
    args_schema: Type[BaseModel] = _ArgsExplicar

    def _run(self, id_transaccion: int) -> str:
        CTX.exigir()
        try:
            idx = int(id_transaccion)
        except (TypeError, ValueError):
            return (
                f"ERROR: '{id_transaccion}' no es un identificador valido. "
                "Debe ser un numero entero obtenido de priorizar_sospechosas."
            )

        # El argumento es un NUMERO DE CASO (1..N), no un indice del DataFrame
        if idx not in CTX.mapa:
            return (
                f"ERROR: no existe el caso {idx}. Los casos van del 1 al "
                f"{len(CTX.mapa)}. Usa priorizar_sospechosas para verlos."
            )

        exp = CTX.detector.explicar(CTX.lote, CTX.mapa[idx])
        texto = exp.a_texto(CTX.dossier)

        # Contexto comparativo: sin el, el LLM no sabe si 1.18 EUR es mucho o poco
        media = CTX.puntuado["Amount"].mean()
        texto += (
            f"\n  Contexto: el importe medio del lote es {media:.2f} EUR, "
            f"asi que esta transaccion esta "
            f"{'por encima' if exp.importe > media else 'por debajo'} de la media."
        )
        return texto


# ----------------------------------------------------------------------
# 4. Rendimiento historico del detector  (Evaluador)
# ----------------------------------------------------------------------
class RendimientoDetectorTool(BaseTool):
    name: str = "rendimiento_del_detector"
    description: str = (
        "Devuelve las metricas de validacion del detector medidas en la fase de "
        "entrenamiento: AUC-PR, precision, recall y precision@N. Usala para saber "
        "cuanto puedes fiarte de sus puntuaciones y que tasa de falsos positivos "
        "cabe esperar. No necesita argumentos."
    )

    def _run(self) -> str:
        import json

        from src.config import REPORTS_DIR

        ruta = REPORTS_DIR / "metricas_detector.json"
        if not ruta.exists():
            return (
                "ERROR: no hay metricas registradas. Ejecuta primero "
                "'python -m src.detector.train'."
            )

        datos = json.loads(ruta.read_text(encoding="utf-8"))
        # El split temporal es el realista: es el que se uso para los modelos
        # que estan en produccion.
        temporal = [d for d in datos if d.get("split") == "temporal"]

        lineas = ["RENDIMIENTO DEL DETECTOR (validacion temporal)", ""]
        for d in temporal:
            lineas.append(f"  {d['modelo']}:")
            lineas.append(f"    AUC-PR    : {d['auc_pr']:.4f} "
                          f"(linea base por azar: {d['prevalencia']:.5f})")
            lineas.append(f"    Precision : {d['precision']:.4f}")
            lineas.append(f"    Recall    : {d['recall']:.4f}")
            for n in TOP_N:
                if f"precision@{n}" in d:
                    lineas.append(f"    De las {n} mas sospechosas, "
                                  f"{d[f'aciertos@{n}']} eran fraude "
                                  f"({d[f'precision@{n}']:.1%})")
            lineas.append("")

        lineas.append(
            "INTERPRETACION: el detector supervisado (XGBoost) es fiable en la "
            "cabeza del ranking pero pierde precision al bajar. El Isolation "
            "Forest, no supervisado, rinde muy por debajo en este lote: trata "
            "sus senales como indicio secundario, nunca como prueba."
        )
        return "\n".join(lineas)


# ----------------------------------------------------------------------
def _lineas_puntuacion(fila) -> list:
    """Lineas de puntuacion del expediente segun el nivel de informacion.

    Aisla en un solo punto que ve el modelo, para que la ablacion sea
    consistente entre el expediente por lotes y el de caso unico.
    """
    if CTX.dossier == "completo":
        return [f"Probabilidad de fraude: {fila['prob_fraude']:.4f}",
                f"Nivel de riesgo: {fila['riesgo']}"]
    if CTX.dossier == "sin_nivel":
        return [f"Probabilidad de fraude: {fila['prob_fraude']:.4f}"]
    return []   # ciego: ni probabilidad ni etiqueta


def construir_dossier() -> str:
    """Expediente completo de los casos a revisar, calculado sin LLM.

    Esta funcion existe por una leccion aprendida a golpes: en la primera
    version, los identificadores de las transacciones viajaban de un agente a
    otro a traves del texto que generaba el LLM. Un modelo de 8B omitio la
    tabla en su respuesta, el siguiente agente se quedo sin identificadores,
    se los invento, la herramienta devolvio errores, y el agente respondio
    fabricando cinco transacciones inexistentes. El informe final era
    impecable en la forma y completamente falso en el fondo.

    La conclusion es de diseno, no de modelo: un camino de datos determinista
    no debe atravesar un componente estocastico. Los hechos se calculan aqui y
    se inyectan en el prompt; al LLM se le pide que narre, no que recuerde.

    SEGUNDA LECCION, aprendida al pasar a turnos reales. Los casos se numeran
    **1..N**, NO con el indice del DataFrame. Con lotes sinteticos los indices
    eran numeros de 1-3 cifras y no daban problema; con turnos reales pasaron a
    ser de 4-5 cifras (15902, 24934...) y el modelo empezo a **corromperlos**:
    escribia 15904 por 15902, 24929 por 24934, 1867 por 1866. Un identificador
    largo se parte en varios tokens y alterar una cifra es trivial. Los numeros
    del 1 al 20 son un token unico y no se confunden.

    La correspondencia con el indice real la guarda `CTX.mapa`, fuera del
    alcance del LLM.
    """
    CTX.exigir()
    casos = CTX.detector.seleccionar_casos(CTX.lote, CTX.capacidad,
                                          CTX.umbral, CTX.minimo)

    bloques = [
        "EXPEDIENTE DE CASOS (datos verificados del detector; no los alteres)",
        "",
    ]
    for n, idx in enumerate(casos.index, start=1):
        fila = casos.loc[idx]
        exp = CTX.detector.explicar(CTX.lote, idx)
        bloques.append(f"--- CASO {n} ---")
        bloques.extend(_lineas_puntuacion(fila))
        bloques.append(f"Importe: {fila['Amount']:.2f} EUR")
        bloques.append(f"Hora del dia: {fila['Hour']:.1f}h")
        bloques.append("Variables de mayor aporte:")
        for var, valor, aporte in exp.contribuciones[:4]:
            sentido = "hacia FRAUDE" if aporte > 0 else "hacia LEGITIMA"
            bloques.append(f"  {var} = {valor:.3f} (aporte {aporte:+.3f}, {sentido})")
        bloques.append("")

    media = CTX.puntuado["Amount"].mean()
    bloques.append(f"Importe medio del lote: {media:.2f} EUR")
    bloques.append(f"Total de casos en el expediente: {len(casos)}")
    return "\n".join(bloques)


def construir_dossier_caso(n: int) -> str:
    """Expediente de UN SOLO caso, para el Investigador iterativo.

    Existe porque pedirle a un modelo local N parrafos en una sola respuesta
    tiene un techo medido: cobertura completa y estable hasta 18 casos, y a
    partir de 20 se vuelve erratica (25 % y 80 % en ejecuciones identicas) sin
    que el modelo avise de las omisiones.

    Con un caso por llamada la cobertura es del 100 % por construccion: si
    falta una explicacion, es porque esa llamada fallo, y se puede reintentar
    de forma aislada. El coste crece linealmente, pero deja de haber un limite
    superior al numero de casos revisables.
    """
    CTX.exigir()
    if n not in CTX.mapa:
        raise KeyError(f"No existe el caso {n}. Casos validos: 1..{len(CTX.mapa)}")

    idx = CTX.mapa[n]
    fila = CTX.puntuado.loc[idx]
    exp = CTX.detector.explicar(CTX.lote, idx)

    lineas = [
        f"CASO {n} (datos verificados del detector; no los alteres)",
        *_lineas_puntuacion(fila),
        f"Importe: {fila['Amount']:.2f} EUR",
        f"Hora del dia: {fila['Hour']:.1f}h",
        "Variables de mayor aporte:",
    ]
    for var, valor, aporte in exp.contribuciones[:4]:
        sentido = "hacia FRAUDE" if aporte > 0 else "hacia LEGITIMA"
        lineas.append(f"  {var} = {valor:.3f} (aporte {aporte:+.3f}, {sentido})")
    lineas.append(f"Importe medio del lote: {CTX.puntuado['Amount'].mean():.2f} EUR")
    return "\n".join(lineas)


def construir_tabla_casos(veredictos: dict = None) -> str:
    """Tabla final del informe, calculada sin LLM.

    Es la ultima aplicacion del principio que ya resolvio la fabricacion de
    transacciones: un camino de datos determinista no debe atravesar un
    componente estocastico.

    ## El problema que resuelve

    Se le pedia al Reportero una tabla con una fila por caso. Con expedientes
    de 32 a 55 casos, el informe cubria SIEMPRE unos catorce, con
    independencia del tamano:

        expediente 55 -> 26 % de cobertura -> 14,2 casos
        expediente 53 -> 27 %              -> 14,5
        expediente 42 -> 35 %              -> 14,5
        expediente 32 -> 45 %              -> 14,5

    No era truncamiento de contexto: al ampliar la ventana a 16k la cobertura
    BAJO al 11 %, porque el modelo dispone de mas espacio y lo emplea en
    escribir un resumen ejecutivo con ejemplos en lugar de enumerar. Es una
    decision de estilo, y por eso pedirlo mejor en el prompt no lo arregla.

    ## La solucion

    La tabla se construye aqui, con los datos del detector y los veredictos ya
    extraidos del texto del Investigador. La cobertura pasa a ser del 100 % por
    construccion. Al modelo se le sigue pidiendo la parte narrativa, que es lo
    que sabe hacer.

    Args:
        veredictos: {numero_de_caso: "CONFIRMADO" | "DESCARTADO"}. Los casos
            sin veredicto se marcan como pendientes, que es informacion util:
            senala exactamente donde fallo la investigacion.
    """
    CTX.exigir()
    casos = CTX.detector.seleccionar_casos(CTX.lote, CTX.capacidad,
                                          CTX.umbral, CTX.minimo)
    veredictos = veredictos or {}

    cabecera = ["| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |",
                "|---|---|---|---|---|"]
    filas = []
    for n, idx in enumerate(casos.index, start=1):
        fila = casos.loc[idx]
        v = veredictos.get(n)
        if v == "DESCARTADO":
            veredicto, accion = "Descartado", "Archivar"
        elif v == "CONFIRMADO":
            veredicto, accion = "Confirmado", "Bloquear tarjeta"
        else:
            veredicto, accion = "Sin veredicto", "Revisar manualmente"
        filas.append(f"| {n} | {fila['Amount']:.2f} | {fila['Hour']:.1f}h | "
                     f"{veredicto} | {accion} |")

    conf = sum(1 for v in veredictos.values() if v == "CONFIRMADO")
    desc = sum(1 for v in veredictos.values() if v == "DESCARTADO")
    sin = len(casos) - conf - desc

    pie = ["", f"**{len(casos)} casos en el expediente**: {conf} confirmados, "
               f"{desc} descartados" + (f", {sin} sin veredicto" if sin else "") + "."]
    return "\n".join(cabecera + filas + pie)


def n_casos() -> int:
    """Cuantos casos hay en el expediente."""
    CTX.exigir()
    return len(CTX.mapa)


def ids_de_casos() -> list:
    """Numeros de caso (1..N) que el LLM debe citar. Para auditar el informe."""
    CTX.exigir()
    return list(CTX.mapa.keys())


def mapa_casos() -> dict:
    """Correspondencia numero de caso -> indice real del DataFrame."""
    CTX.exigir()
    return dict(CTX.mapa)


def herramientas_disponibles() -> dict:
    """Instancia todas las herramientas, para repartirlas entre los agentes."""
    return {
        "estadisticas": EstadisticasLoteTool(),
        "priorizar": PriorizarSospechosasTool(),
        "explicar": ExplicarTransaccionTool(),
        "rendimiento": RendimientoDetectorTool(),
    }
