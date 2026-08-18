"""
Demostrador web del sistema antifraude.

## Para que existe

La memoria describe un sistema de dos capas y mide lo que aporta la segunda.
Pero un lector -o un tribunal- no puede juzgar esa medida sin ver lo que el
modelo de lenguaje recibe y lo que devuelve. Este demostrador hace visible
justo eso: el expediente que produce el detector, el dossier exacto de un caso
tal como llega al prompt, y las dos salidas del Investigador puestas una al
lado de la otra.

La pantalla de investigacion no es un adorno. Muestra el parrafo explicativo y
el veredicto en columnas separadas porque el resultado central del trabajo es
que no se corresponden, y eso se aprecia leyendolos juntos mucho mejor que en
una tabla de porcentajes.

## Que NO hace

No reentrena nada ni sustituye a los guiones de experimentacion. Lee los
mismos modelos ya entrenados y llama a las mismas funciones que ellos, de modo
que lo que se ve por pantalla es el sistema, no una reimplementacion que
podria divergir.

Uso:
    uvicorn src.web.app:app --reload --port 8000
    python -m src.web.app          # equivalente, sin recarga automatica
"""

import time
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import CASOS_MAX, LLM_MODEL, OLLAMA_HOST, TARGET_COL
from src.detector.data import cargar_dataset
from src.detector.predict import DetectorFraude, construir_turno

ESTATICO = Path(__file__).resolve().parent / "estatico"

app = FastAPI(title="Departamento antifraude — demostrador")


# ----------------------------------------------------------------------
# Estado del proceso
#
# El dataset son 150 MB y el detector tarda en cargar. Se mantienen vivos
# entre peticiones en lugar de recargarlos cada vez. Es un demostrador de un
# solo usuario en local: no hay concurrencia que proteger.
# ----------------------------------------------------------------------
class Estado:
    def __init__(self):
        self.df = None
        self.detector = None
        self.turno = None
        self.casos = None          # expediente: DataFrame de casos elevados
        self.mapa = {}             # numero de caso -> indice real
        self.parametros = {}

    def cargar(self):
        if self.df is None:
            self.df = cargar_dataset()
        if self.detector is None:
            self.detector = DetectorFraude()
        return self


E = Estado()


class ParametrosTurno(BaseModel):
    horas: float = 4.0
    desplazamiento: float = 0.0
    umbral: float = 0.05
    capacidad: int = CASOS_MAX


# ----------------------------------------------------------------------
@app.get("/api/estado")
def estado():
    """Que hay disponible antes de empezar. Se consulta al abrir la pagina."""
    import requests
    from src.config import DATASET_CSV, MODELS_DIR

    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        modelos = sorted(m["name"] for m in r.json().get("models", []))
        ollama = True
    except Exception:
        modelos, ollama = [], False

    # El turno vive en el proceso, no en el navegador. Al recargar la pagina
    # el cliente lo olvida y el servidor no, de modo que la interfaz pedia
    # casos de un expediente que creia tener y respondia "no existe" sin
    # explicar cual estaba realmente cargado. Se devuelve aqui para que el
    # cliente pueda reconstruir su estado al abrirse.
    turno = None
    if E.casos is not None:
        turno = {
            "parametros": E.parametros,
            "resumen": {
                "transacciones": int(len(E.turno)),
                "fraudes_reales": int(E.turno[TARGET_COL].sum()),
                "casos_elevados": len(E.mapa),
                "fraude_en_expediente": int(E.casos[TARGET_COL].sum()),
            },
        }

    return {
        "dataset": DATASET_CSV.exists(),
        "modelo_detector": (MODELS_DIR / "xgboost_fraude.json").exists(),
        "ollama": ollama,
        "modelos_llm": modelos,
        "modelo_por_defecto": LLM_MODEL,
        "turno": turno,
    }


@app.post("/api/turno")
def crear_turno(p: ParametrosTurno):
    """Construye un turno, lo puntua y devuelve el expediente."""
    E.cargar()
    t0 = time.perf_counter()
    try:
        E.turno = construir_turno(E.df, horas=p.horas,
                                  desplazamiento_h=p.desplazamiento)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    E.casos = E.detector.seleccionar_casos(E.turno, p.capacidad, p.umbral,
                                           minimo=0)
    E.mapa = {n: idx for n, idx in enumerate(E.casos.index, start=1)}
    E.parametros = p.model_dump()
    ms = (time.perf_counter() - t0) * 1000

    puntuado = E.detector.puntuar(E.casos)
    filas = []
    for n, idx in E.mapa.items():
        fila = E.casos.loc[idx]
        filas.append({
            "n": n,
            "id": int(idx),
            "probabilidad": float(puntuado.loc[idx, "prob_fraude"]),
            "riesgo": str(puntuado.loc[idx, "riesgo"]),
            "importe": float(fila["Amount"]),
            "hora": float(fila.get("Hour", 0)),
            # La clase real se envia para poder colorear aciertos y fallos en
            # el demostrador. El sistema NUNCA la ve: no entra en el dossier.
            "es_fraude": bool(fila[TARGET_COL] == 1),
        })

    return {
        "parametros": E.parametros,
        "resumen": {
            "transacciones": int(len(E.turno)),
            "fraudes_reales": int(E.turno[TARGET_COL].sum()),
            "casos_elevados": len(filas),
            "fraude_en_expediente": sum(1 for f in filas if f["es_fraude"]),
            "ms_deteccion": round(ms, 1),
        },
        "casos": filas,
    }


@app.get("/api/caso/{n}")
def caso(n: int, dossier: str = "completo"):
    """El caso n tal como lo ve el modelo, y las cifras que hay detras.

    El parametro `dossier` reproduce la ablacion de la seccion 5.7: permite
    ver en pantalla exactamente que informacion se le retira al modelo en cada
    nivel, que es mas convincente que describirlo.
    """
    if E.casos is None:
        raise HTTPException(status_code=409, detail="No hay turno cargado.")
    if n not in E.mapa:
        raise HTTPException(status_code=404, detail=f"El caso {n} no existe.")

    idx = E.mapa[n]
    exp = E.detector.explicar(E.casos, idx)
    fila = E.casos.loc[idx]
    return {
        "n": n,
        "id": int(idx),
        "es_fraude": bool(fila[TARGET_COL] == 1),
        "probabilidad": float(exp.probabilidad),
        "riesgo": exp.riesgo,
        "importe": float(exp.importe),
        "hora": float(exp.hora),
        "contribuciones": [
            {"variable": v, "valor": float(val), "aporte": float(ap)}
            for v, val, ap in exp.contribuciones
        ],
        # El texto EXACTO que se incrusta en el prompt, sin reformatear.
        "dossier": exp.a_texto(dossier),
        "nivel_dossier": dossier,
    }


class PeticionInvestigar(BaseModel):
    modelo: str | None = None
    dominio: bool = False
    max_tokens: int = 220


@app.post("/api/investigar/{n}")
def investigar(n: int, p: PeticionInvestigar):
    """Ejecuta el Investigador sobre un solo caso y separa sus dos salidas.

    Se invoca al modelo directamente, sin CrewAI, por la misma razon que en
    scripts/investigador_solo.py: la orquestacion introduce reintentos y
    limites propios que contaminarian el tiempo medido. El enunciado es el
    mismo que usa ese guion, importado de el, de modo que lo que se ve aqui es
    lo que producen los experimentos.
    """
    if E.casos is None:
        raise HTTPException(status_code=409, detail="No hay turno cargado.")
    if n not in E.mapa:
        raise HTTPException(status_code=404, detail=f"El caso {n} no existe.")

    import importlib.util
    import requests
    from src.agents.tools import construir_dossier_caso, inicializar_contexto
    from src.evaluacion import veredictos_por_caso

    inicializar_contexto(E.turno, E.detector,
                         capacidad=E.parametros["capacidad"],
                         umbral=E.parametros["umbral"], minimo=0)

    ruta = Path(__file__).resolve().parent.parent.parent / "scripts" / "investigador_solo.py"
    spec = importlib.util.spec_from_file_location("inv_solo", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prompt = mod.construir_prompt(n, construir_dossier_caso(n), p.dominio)

    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{OLLAMA_HOST.rstrip('/')}/api/generate",
            json={"model": p.modelo or LLM_MODEL, "prompt": prompt,
                  "stream": False,
                  "options": {"num_predict": p.max_tokens, "temperature": 0.1}},
            timeout=600,
        )
        r.raise_for_status()
        d = r.json()
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"No se pudo hablar con Ollama: {e}")
    seg = time.perf_counter() - t0

    texto = (d.get("response") or "").strip()
    pensado = (d.get("thinking") or "").strip()
    # Ollama declara por que se detuvo: "stop" si el modelo termino por su
    # cuenta, "length" si choco contra el limite de tokens. Sin mirar este
    # campo, una respuesta truncada a mitad de frase es indistinguible de una
    # en la que el modelo simplemente omitio el veredicto, y la interfaz
    # mostraba "no reconocido" sin decir cual de las dos cosas habia pasado.
    motivo = d.get("done_reason", "")
    truncado = motivo == "length"

    aviso = None
    if not texto and pensado:
        aviso = (f"El modelo agoto los {p.max_tokens} tokens razonando y no "
                 f"llego a emitir respuesta. Es un modelo de razonamiento: "
                 f"gasta el presupuesto pensando antes de escribir. Sube el "
                 f"limite.")
    elif truncado:
        aviso = (f"La respuesta se corto al alcanzar los {p.max_tokens} "
                 f"tokens, antes de llegar al veredicto. Lo que se ve abajo "
                 f"esta incompleto. Sube el limite.")
    elif not texto:
        aviso = f"El modelo devolvio una respuesta vacia (motivo: {motivo or 'desconocido'})."

    ver = veredictos_por_caso(texto).get(n)
    # Se separa la prosa del veredicto para poder mostrarlos enfrentados: es
    # la disociacion que mide la seccion 5.12 de la memoria.
    prosa = texto
    m = mod.re.search(r"(?:VEREDICTO|VERDICT)\s*:", texto, mod.re.IGNORECASE)
    if m:
        prosa = texto[:m.start()].strip()

    return {
        "n": n, "modelo": p.modelo or LLM_MODEL, "dominio": p.dominio,
        "segundos": round(seg, 2),
        "prosa": prosa,
        "veredicto": ver,
        "texto_completo": texto,
        "aviso": aviso,
        "truncado": truncado,
        "motivo_parada": motivo,
        "tokens_generados": d.get("eval_count"),
        "es_fraude": bool(E.casos.loc[E.mapa[n]][TARGET_COL] == 1),
        "prompt": prompt,
    }


class PeticionInforme(BaseModel):
    modelo: str | None = None
    modo: str = "revisa"


@app.post("/api/informe")
def informe(p: PeticionInforme):
    """Ejecuta el departamento completo y audita el informe resultante.

    Tarda minutos: es la unica pantalla del demostrador que no responde al
    instante, y la interfaz avisa de ello. Se conserva porque ver los seis
    agentes turnandose es lo que hace comprensible la arquitectura.
    """
    if E.turno is None:
        raise HTTPException(status_code=409, detail="No hay turno cargado.")

    from src.agents.crew import construir_crew
    from src.agents.tools import (construir_tabla_casos, inicializar_contexto,
                                  mapa_casos)
    from src.evaluacion import auditar, medir_sistema, veredictos_por_caso

    inicializar_contexto(E.turno, E.detector,
                         capacidad=E.parametros["capacidad"],
                         umbral=E.parametros["umbral"], minimo=0)
    t0 = time.perf_counter()
    crew = construir_crew(modo=p.modo, modelo=p.modelo)
    salida = str(crew.kickoff())
    seg = time.perf_counter() - t0

    mapa = mapa_casos()
    ver = veredictos_por_caso(salida)
    met = medir_sistema(E.turno, E.detector, salida, p.modo,
                        capacidad=E.parametros["capacidad"],
                        mapa_casos=mapa, umbral=E.parametros["umbral"])
    # El informe cita NUMEROS DE CASO (1..N), no indices del DataFrame. La
    # primera version pasaba al auditor los indices reales, de modo que un
    # informe perfectamente valido salia con cobertura 0 % y con los 55
    # numeros de caso marcados como "citas fuera del expediente". Es la misma
    # convencion que usa scripts/experimento.py: se audita contra
    # met["ids_expediente"], que son los numeros que el modelo maneja.
    aud = auditar(salida, met["ids_expediente"], met["ids_expediente"])

    return {
        "modo": p.modo, "modelo": p.modelo or LLM_MODEL,
        "segundos": round(seg, 1),
        "informe": salida,
        "tabla": construir_tabla_casos(ver),
        "veredictos": {str(k): v for k, v in ver.items()},
        "auditoria": aud,
        "metricas": {k: (round(v, 4) if isinstance(v, float) else v)
                     for k, v in met.items()
                     if not isinstance(v, (list, dict)) and k != "modo"},
        # Cuantos casos quedaron sin veredicto: en modo revisa es el dato que
        # delata una extraccion parcial, que de otro modo pasa en silencio.
        "sin_veredicto": len(mapa) - len(ver),
    }


# ----------------------------------------------------------------------
# Estaticos. Se montan al final para que las rutas /api tengan prioridad.
# ----------------------------------------------------------------------
@app.get("/")
def raiz():
    return FileResponse(ESTATICO / "index.html")


app.mount("/", StaticFiles(directory=ESTATICO), name="estatico")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web.app:app", host="127.0.0.1", port=8000, reload=False)
