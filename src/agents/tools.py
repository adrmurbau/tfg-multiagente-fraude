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
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.config import TOP_N
from src.detector.predict import DetectorFraude


# ----------------------------------------------------------------------
# Contexto compartido
# ----------------------------------------------------------------------
class _Contexto:
    """Detector y lote activos. Se inicializa una vez por ejecucion."""

    def __init__(self):
        self.detector: DetectorFraude | None = None
        self.lote: pd.DataFrame | None = None
        self.puntuado: pd.DataFrame | None = None

    def inicializar(self, lote: pd.DataFrame, detector: DetectorFraude = None):
        self.detector = detector or DetectorFraude()
        self.lote = lote
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


def inicializar_contexto(lote: pd.DataFrame, detector: DetectorFraude = None):
    """Prepara el lote que analizara el departamento."""
    return CTX.inicializar(lote, detector)


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
        conteo = p["riesgo"].value_counts()

        return (
            f"LOTE BAJO ANALISIS\n"
            f"  Transacciones            : {len(p):,}\n"
            f"  Riesgo ALTO (rojo)       : {conteo.get('ALTO', 0)}\n"
            f"  Riesgo MEDIO (ambar)     : {conteo.get('MEDIO', 0)}\n"
            f"  Riesgo BAJO (verde)      : {conteo.get('BAJO', 0)}\n"
            f"  Probabilidad maxima      : {p['prob_fraude'].max():.4f}\n"
            f"  Probabilidad media       : {p['prob_fraude'].mean():.4f}\n"
            f"  Importe total del lote   : {p['Amount'].sum():,.2f} EUR\n"
            f"  Importe en riesgo        : "
            f"{p.loc[p['riesgo'] != 'BAJO', 'Amount'].sum():,.2f} EUR\n"
            f"  Importe medio            : {p['Amount'].mean():.2f} EUR\n"
            f"  Franja horaria           : {p['Hour'].min():.1f}h - {p['Hour'].max():.1f}h"
        )


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

        filas = [f"TOP {n} TRANSACCIONES SOSPECHOSAS", ""]
        filas.append(f"{'id':>6} {'prob':>8} {'riesgo':>7} {'importe':>11} {'hora':>6}")
        filas.append("-" * 42)
        for idx, f in top.iterrows():
            filas.append(
                f"{idx:>6} {f['prob_fraude']:>8.4f} {f['riesgo']:>7} "
                f"{f['Amount']:>11.2f} {f['Hour']:>6.1f}"
            )

        altos = int((top["riesgo"] == "ALTO").sum())
        filas.append("")
        filas.append(f"De estas {n}, {altos} superan el umbral de riesgo ALTO (0.80).")
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

        if idx not in CTX.lote.index:
            disponibles = list(CTX.lote.index[:5])
            return (
                f"ERROR: no existe la transaccion {idx} en este lote. "
                f"Identificadores validos, por ejemplo: {disponibles}. "
                "Usa priorizar_sospechosas para obtener identificadores correctos."
            )

        exp = CTX.detector.explicar(CTX.lote, idx)
        texto = exp.a_texto()

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
    """
    CTX.exigir()
    casos = CTX.detector.seleccionar_casos(CTX.lote)

    bloques = [
        "EXPEDIENTE DE CASOS (datos verificados del detector; no los alteres)",
        "",
    ]
    for idx, fila in casos.iterrows():
        exp = CTX.detector.explicar(CTX.lote, idx)
        bloques.append(f"--- CASO {idx} ---")
        bloques.append(f"Probabilidad de fraude: {fila['prob_fraude']:.4f}")
        bloques.append(f"Nivel de riesgo: {fila['riesgo']}")
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


def ids_de_casos() -> list:
    """Identificadores de los casos seleccionados, para verificar el informe."""
    CTX.exigir()
    return list(CTX.detector.seleccionar_casos(CTX.lote).index)


def herramientas_disponibles() -> dict:
    """Instancia todas las herramientas, para repartirlas entre los agentes."""
    return {
        "estadisticas": EstadisticasLoteTool(),
        "priorizar": PriorizarSospechosasTool(),
        "explicar": ExplicarTransaccionTool(),
        "rendimiento": RendimientoDetectorTool(),
    }
