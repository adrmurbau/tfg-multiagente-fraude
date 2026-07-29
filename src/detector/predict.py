"""
Inferencia y explicacion del detector - la herramienta que usaran los agentes.

Este modulo NO sabe nada de LLMs ni de CrewAI a proposito. Es la capa 1 pura:
carga los modelos entrenados, puntua transacciones y explica por que cada una
resulta sospechosa. La capa 2 (src/agents/tools.py) se limita a envolverlo.

Separarlo asi tiene una ventaja practica: todo lo de aqui se puede probar sin
levantar un modelo de lenguaje, de modo que cuando algo falle en la Fase 3
sabras si el problema es el LLM o el detector.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import xgboost as xgb

from src.config import (
    FEATURE_COLS,
    MODELS_DIR,
    PCA_COLS,
    RISK_THRESHOLDS,
    TARGET_COL,
)

XGB_PATH = MODELS_DIR / "xgboost_fraude.json"
IFOREST_PATH = MODELS_DIR / "iforest_fraude.pkl"


def semaforo(prob: float) -> str:
    """Traduce una probabilidad al semaforo de riesgo del informe."""
    if prob >= RISK_THRESHOLDS["ALTO"]:
        return "ALTO"
    if prob >= RISK_THRESHOLDS["MEDIO"]:
        return "MEDIO"
    return "BAJO"


@dataclass
class Explicacion:
    """Descomposicion de una prediccion en contribuciones por variable."""
    indice: int
    probabilidad: float
    riesgo: str
    importe: float
    hora: float
    contribuciones: list = field(default_factory=list)  # [(variable, valor, aporte)]

    def a_texto(self) -> str:
        """Version narrativa, pensada para meterse en el prompt de un agente."""
        lineas = [
            f"Transaccion #{self.indice}",
            f"  Probabilidad de fraude: {self.probabilidad:.4f} (riesgo {self.riesgo})",
            f"  Importe: {self.importe:.2f} EUR | Hora del dia: {self.hora:.1f}h",
            "  Variables que mas empujan la decision:",
        ]
        for var, valor, aporte in self.contribuciones:
            sentido = "hacia FRAUDE" if aporte > 0 else "hacia LEGITIMA"
            lineas.append(
                f"    {var:>8} = {valor:>10.3f}  ->  aporte {aporte:+.3f} ({sentido})"
            )
        return "\n".join(lineas)


class DetectorFraude:
    """Envoltorio sobre los dos modelos entrenados en la Fase 2."""

    def __init__(self, cargar_iforest: bool = True):
        if not XGB_PATH.exists():
            raise FileNotFoundError(
                f"No se encuentra {XGB_PATH}. Entrena primero: "
                "python -m src.detector.train"
            )
        self.xgb = xgb.XGBClassifier()
        self.xgb.load_model(XGB_PATH)
        self.booster = self.xgb.get_booster()

        self.iforest = None
        if cargar_iforest and IFOREST_PATH.exists():
            import joblib
            self.iforest = joblib.load(IFOREST_PATH)

    # ------------------------------------------------------------------
    def puntuar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Anade probabilidad, semaforo y (si procede) score de anomalia."""
        X = df[FEATURE_COLS]
        out = df.copy()
        out["prob_fraude"] = self.xgb.predict_proba(X)[:, 1]
        out["riesgo"] = [semaforo(p) for p in out["prob_fraude"]]

        if self.iforest is not None:
            bruto = -self.iforest.named_steps["iforest"].score_samples(
                self.iforest.named_steps["escalado"].transform(X)
            )
            lo, hi = bruto.min(), bruto.max()
            out["score_anomalia"] = (bruto - lo) / (hi - lo) if hi > lo else 0.0

        return out

    def top_sospechosas(self, df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
        """Las n transacciones mas sospechosas, ordenadas de mayor a menor."""
        return self.puntuar(df).nlargest(n, "prob_fraude")

    # ------------------------------------------------------------------
    def explicar(self, df: pd.DataFrame, indice, top_k: int = 6) -> Explicacion:
        """Descompone una prediccion en aportes por variable.

        Usa `pred_contribs=True` de XGBoost, que calcula valores SHAP exactos
        para modelos de arboles sin necesidad de instalar la libreria `shap`.
        La suma de todos los aportes mas el sesgo da el log-odds de la
        prediccion, asi que la explicacion es fiel al modelo, no una
        aproximacion post-hoc.
        """
        fila = df.loc[[indice]]
        X = fila[FEATURE_COLS]

        contribs = self.booster.predict(
            xgb.DMatrix(X, feature_names=list(FEATURE_COLS)),
            pred_contribs=True,
        )[0]
        aportes = contribs[:-1]   # el ultimo elemento es el sesgo base

        # Ordenar por magnitud del aporte, con signo conservado
        orden = np.argsort(-np.abs(aportes))[:top_k]
        detalle = [
            (FEATURE_COLS[i], float(X.iloc[0, i]), float(aportes[i]))
            for i in orden
        ]

        prob = float(self.xgb.predict_proba(X)[0, 1])
        return Explicacion(
            indice=int(indice),
            probabilidad=prob,
            riesgo=semaforo(prob),
            importe=float(fila["Amount"].iloc[0]),
            hora=float(fila["Hour"].iloc[0]),
            contribuciones=detalle,
        )

    # ------------------------------------------------------------------
    def resumen_lote(self, df: pd.DataFrame) -> dict:
        """Estadisticas agregadas de un lote ya puntuado."""
        p = self.puntuar(df)
        conteo = p["riesgo"].value_counts().to_dict()
        return {
            "n_transacciones": len(p),
            "riesgo_alto": conteo.get("ALTO", 0),
            "riesgo_medio": conteo.get("MEDIO", 0),
            "riesgo_bajo": conteo.get("BAJO", 0),
            "prob_max": float(p["prob_fraude"].max()),
            "prob_media": float(p["prob_fraude"].mean()),
            "importe_total": float(p["Amount"].sum()),
            "importe_en_riesgo": float(p.loc[p["riesgo"] != "BAJO", "Amount"].sum()),
        }


    # ------------------------------------------------------------------
    def seleccionar_casos(self, df: pd.DataFrame, capacidad: int = None) -> pd.DataFrame:
        """Decide que casos se elevan a revision.

        Regla: todos los de riesgo ALTO. Si hay menos de CASOS_MIN se completa
        con los siguientes por puntuacion (para que el informe nunca salga
        vacio) y se corta en la capacidad de revision.

        Un corte fijo por posicion seria peor: dejaria fuera casos en rojo por
        el mero hecho de ocupar un puesto bajo en el ranking.

        `capacidad` modela la **capacidad de revision manual** del equipo: un
        departamento real no revisa todo lo que el modelo marca, revisa lo que
        le da tiempo. Por defecto CASOS_MAX.
        """
        from src.config import CASOS_MAX, CASOS_MIN

        tope = capacidad if capacidad is not None else CASOS_MAX
        p = self.puntuar(df)
        altos = p[p["riesgo"] == "ALTO"].sort_values("prob_fraude", ascending=False)

        if len(altos) >= CASOS_MIN:
            return altos.head(tope)
        return p.nlargest(max(CASOS_MIN, min(tope, len(p))), "prob_fraude")


# ----------------------------------------------------------------------
def construir_lote(df: pd.DataFrame, n: int = 500, n_fraudes: int = 5,
                   random_state: int = 42) -> pd.DataFrame:
    """Construye un lote de trabajo realista para que lo analice el departamento.

    Mezcla transacciones legitimas con unos pocos fraudes conocidos. Las
    etiquetas viajan en el lote pero NI el detector NI los agentes las miran:
    se reservan para que el Evaluador mida el acierto del sistema al final.
    """
    periodo_test = df.sort_values("Time").iloc[int(len(df) * 0.8):]

    fraudes = periodo_test[periodo_test[TARGET_COL] == 1]
    n_fraudes = min(n_fraudes, len(fraudes))
    muestra_fraude = fraudes.sample(n_fraudes, random_state=random_state)

    legitimas = periodo_test[periodo_test[TARGET_COL] == 0].sample(
        n - n_fraudes, random_state=random_state
    )

    lote = pd.concat([muestra_fraude, legitimas]).sample(
        frac=1, random_state=random_state
    )
    return lote.reset_index(drop=True)


def construir_turno(df: pd.DataFrame, horas: float = 4.0,
                    desplazamiento_h: float = 0.0) -> pd.DataFrame:
    """Extrae una ventana temporal CONTIGUA del periodo de test.

    A diferencia de `construir_lote`, que toma una muestra aleatoria con un
    numero fijo de fraudes, esto reproduce lo que un departamento recibiria de
    verdad: **todas** las transacciones de un intervalo, con la proporcion de
    fraude que tenga la realidad.

    Por que importa el cambio. Un lote de 500 transacciones con 5 fraudes es
    una construccion artificial: ni el tamano ni la proporcion corresponden a
    nada. Un turno de 4 horas son ~33.000 transacciones con ~54 fraudes, que es
    lo que de verdad pasa por un sistema real. Y multiplica por diez el numero
    de fraudes evaluables, con lo que el recall deja de moverse a saltos de 0,2.

    El coste NO se dispara: puntuar 33.000 transacciones es instantaneo, y a la
    capa de agentes solo llegan los casos que el detector eleva.

    Args:
        horas: duracion del turno.
        desplazamiento_h: desde donde empieza, dentro del periodo de test.

    LIMITACION: el periodo de test dura 7,7 horas, asi que turnos de 4 h
    partiendo de desplazamientos distintos **se solapan**. No son muestras
    independientes y hay que declararlo al interpretar la variabilidad entre
    turnos.
    """
    ordenado = df.sort_values("Time")
    inicio_test = ordenado["Time"].iloc[int(len(ordenado) * 0.8)]

    desde = inicio_test + desplazamiento_h * 3600
    hasta = desde + horas * 3600

    turno = ordenado[(ordenado["Time"] >= desde) & (ordenado["Time"] < hasta)]
    if turno.empty:
        raise ValueError(
            f"Turno vacio: el periodo de test va de "
            f"{inicio_test / 3600:.1f}h a {ordenado['Time'].max() / 3600:.1f}h. "
            f"Reduce --turno-horas o --desplazamiento."
        )
    return turno.reset_index(drop=True)
