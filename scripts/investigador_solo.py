"""
El Investigador aislado, con backend intercambiable - objetivo especifico 4.

Ejecuta UNICAMENTE la tarea de investigacion, con exactamente el mismo prompt
que recibe dentro del sistema completo, contra dos motores distintos:

    ollama   modelos que caben en la VRAM disponible (hasta ~20B en 16 GB)
    airllm   modelos que NO caben, cargando una capa cada vez desde disco

## Por que aislar al Investigador

Los veredictos que producen las metricas salen de ese agente y solo de el. El
Modelador se limita a presentar los casos y el Reportero ensambla una tabla que
desde la ultima version se calcula sin LLM. Ejecutar el crew completo para
comparar motores gastaria tiempo en dos agentes que no influyen en lo medido.

Al usar el mismo prompt y la misma funcion de medida, los resultados son
directamente comparables con los de scripts/experimento.py. Para que la
comparacion sea limpia conviene ejecutar TAMBIEN los modelos pequenos por esta
via, y no contrastar un resultado de aqui contra uno del crew completo.

## Por que AirLLM

El objetivo especifico 4 pide cuantificar cuanto se pierde frente a modelos de
mayor capacidad. La via evidente serian las APIs comerciales, pero eso viola la
restriccion de partida del trabajo: ejecucion integramente local, sin enviar
datos a terceros y sin coste.

AirLLM mantiene una sola capa en GPU cada vez, de modo que la memoria necesaria
depende del tamano de capa y no del modelo completo. Permite ejecutar modelos
de 70B o mas en 16 GB de VRAM sin romper la restriccion. El precio es la
velocidad: cada token exige leer capas desde disco.

## Advertencias antes de lanzarlo

  - ESPACIO EN DISCO. Descomponer un modelo por capas ocupa aproximadamente lo
    mismo que el modelo original. Un 70B en precision reducida ronda los 40 GB;
    en precision completa, mas de 140. El guion comprueba el espacio libre
    antes de empezar.
  - TIEMPO. La primera ejecucion descarga y descompone el modelo, lo que puede
    llevar horas. Conviene empezar con pocos casos.
  - Es una DEMOSTRACION, no una serie estadistica. Con dos o tres ejecuciones
    no hay contraste posible, y asi debe reportarse.

Uso:
    python scripts/investigador_solo.py --backend ollama --modelo qwen2.5-14b-ctx16k --max-casos 12
    python scripts/investigador_solo.py --backend airllm --modelo Qwen/Qwen3-32B --max-casos 5
"""

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import OLLAMA_HOST, REPORTS_DIR, TARGET_COL  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_turno  # noqa: E402
from src.evaluacion import medir_sistema, veredictos_por_caso  # noqa: E402

GB = 1024 ** 3


def parsear_args():
    p = argparse.ArgumentParser(description="Investigador aislado, backend intercambiable")
    p.add_argument("--backend", choices=("ollama", "airllm"), default="ollama")
    p.add_argument("--modelo", required=True,
                   help="ollama: nombre del modelo. airllm: repo de Hugging Face.")
    p.add_argument("--turno-horas", type=float, default=4.0)
    p.add_argument("--desplazamiento", type=float, default=0.0)
    p.add_argument("--umbral", type=float, default=0.05)
    p.add_argument("--capacidad", type=int, default=60)
    p.add_argument("--max-casos", type=int, default=10,
                   help="Cuantos casos investigar. Con airllm, empieza bajo.")
    p.add_argument("--zona", choices=("cabeza", "cola"), default="cola",
                   help="Que parte del expediente investigar. cabeza: los casos "
                        "de mayor probabilidad, que todo modelo confirma y por "
                        "tanto no discriminan. cola: los de menor probabilidad, "
                        "donde se producen los descartes y donde los modelos se "
                        "diferencian. Por defecto cola.")
    p.add_argument("--max-tokens", type=int, default=220,
                   help="Tokens de respuesta por caso.")
    p.add_argument("--disco-minimo-gb", type=int, default=50,
                   help="Espacio libre exigido antes de usar airllm.")
    p.add_argument("--compresion", choices=("ninguna", "4bit", "8bit"),
                   default="4bit",
                   help="Cuantizacion por bloques de AirLLM. Reduce el tamano "
                        "en disco y acelera la carga de capas, que es el cuello "
                        "de botella. Con 4bit un modelo de 70B baja de unos "
                        "140 GB a unos 40. Por defecto 4bit.")
    p.add_argument("--hf-token", default=None,
                   help="Token de Hugging Face, necesario para modelos con "
                        "acceso restringido como los de Meta.")
    return p.parse_args()


# ----------------------------------------------------------------------
# Prompt: identico al de la tarea del Investigador en modo revisa iterativo
# ----------------------------------------------------------------------
def construir_prompt(n: int, dossier_caso: str) -> str:
    """Replica el prompt de src/agents/crew.py para el caso n.

    Se reproduce aqui en lugar de importarlo porque alli vive dentro de la
    construccion de un objeto Task de CrewAI, del que este guion prescinde.
    Cualquier cambio en aquel debe reflejarse en este, o la comparacion entre
    motores dejaria de ser valida.

    ATENCION al bloque de salida esperada. CrewAI concatena en el prompt real
    la descripcion de la tarea Y su `expected_output`, y es este segundo el
    unico sitio donde aparece el literal 'VEREDICTO: CONFIRMADO'. Una primera
    version de este guion replico solo la descripcion, y el modelo respondio
    escribiendo 'DESCARTADO' a secas en una linea aparte -exactamente lo que
    la descripcion le pedia-, de modo que el regex de extraccion no reconocio
    ni un solo veredicto en diez casos.

    El formato del que depende toda la medicion procede, por tanto, de la
    parte del prompt que menos parece contener instrucciones.
    """
    from src.agents.crew import IDIOMA, PROHIBICIONES

    veredicto = (
        "Para CADA caso emite ademas un veredicto: CONFIRMADO si las "
        "evidencias respaldan la sospecha, o DESCARTADO si crees que es un "
        "falso positivo. Se conservador: descartar un fraude real es mucho "
        "mas caro que revisar de mas. Escribe el veredicto en MAYUSCULAS al "
        "final de cada caso, en una linea aparte."
    )
    # Replica del expected_output de la tarea. Sin esto el modelo omite el
    # prefijo y la extraccion de veredictos devuelve cero.
    salida_esperada = (
        f"La linea 'CASO {n}' seguida de un parrafo explicativo en prosa. "
        f"Cada caso termina con una linea 'VEREDICTO: CONFIRMADO' o "
        f"'VEREDICTO: DESCARTADO'."
    )
    return (
        "Eres un investigador de fraude. Explicas por que el detector considera "
        "sospechosa cada transaccion." + IDIOMA + "\n\n"
        f"{dossier_caso}\n\n"
        f"Redacta UN SOLO parrafo de 3 a 5 frases explicando en lenguaje llano "
        f"por que el detector considera sospechoso el CASO {n}. Menciona su "
        f"importe y las variables de mayor aporte tal y como aparecen arriba.\n"
        f"FORMATO: empieza con la linea 'CASO {n}' y debajo el parrafo en "
        f"prosa. Sin tablas ni vinetas.\n"
        + PROHIBICIONES + veredicto
        + f"\n\nEsto es lo que se espera de tu respuesta: {salida_esperada}"
    )


# ----------------------------------------------------------------------
# Backends
# ----------------------------------------------------------------------
def generar_ollama(modelo: str, prompt: str, max_tokens: int) -> str:
    """Llamada directa a la API de Ollama, sin pasar por CrewAI.

    Se evita CrewAI a proposito: introduce reintentos y limites propios que
    contaminarian la medida de tiempo por caso.
    """
    import requests
    r = requests.post(
        f"{OLLAMA_HOST.rstrip('/')}/api/generate",
        json={"model": modelo, "prompt": prompt, "stream": False,
              "options": {"num_predict": max_tokens, "temperature": 0.1}},
        timeout=1800,
    )
    r.raise_for_status()
    return r.json().get("response", "")


class MotorAirLLM:
    """Envoltorio sobre AirLLM. El modelo se carga una sola vez."""

    def __init__(self, repo: str, compresion: str = "4bit", hf_token: str = None):
        try:
            from airllm import AutoModel
        except ImportError:
            print("\n  Falta airllm. Instalalo con:\n      pip install airllm\n")
            sys.exit(1)

        kw = {}
        if compresion != "ninguna":
            # La cuantizacion por bloques solo afecta a los PESOS, no a las
            # activaciones. Aqui el cuello de botella es leer capas desde
            # disco, asi que reducir su tamano acelera de forma directa y con
            # una perdida de precision menor que una cuantizacion completa.
            try:
                import bitsandbytes  # noqa: F401
            except ImportError:
                print("\n  La compresion requiere bitsandbytes:")
                print("      pip install -U bitsandbytes\n")
                sys.exit(1)
            kw["compression"] = compresion
        if hf_token:
            kw["hf_token"] = hf_token

        print(f"  Cargando {repo} con AirLLM"
              + (f", compresion {compresion}" if compresion != "ninguna" else "")
              + ".")
        print("  La primera vez descarga y descompone el modelo por capas:")
        print("  puede tardar horas y ocupa en disco lo que ocupe el modelo.\n")
        t0 = time.perf_counter()
        self.modelo = AutoModel.from_pretrained(repo, **kw)
        print(f"  Modelo listo en {(time.perf_counter()-t0)/60:.1f} min\n")

    def generar(self, prompt: str, max_tokens: int) -> str:
        tok = self.modelo.tokenizer(
            [prompt], return_tensors="pt", return_attention_mask=False,
            truncation=True, max_length=2048, padding=False)
        salida = self.modelo.generate(
            tok["input_ids"].cuda(), max_new_tokens=max_tokens,
            use_cache=True, return_dict_in_generate=True)
        texto = self.modelo.tokenizer.decode(salida.sequences[0])
        # El modelo devuelve el prompt seguido de la continuacion; se recorta.
        return texto[len(prompt):] if texto.startswith(prompt) else texto


# ----------------------------------------------------------------------
def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("  INVESTIGADOR AISLADO")
    print("=" * 70)
    print(f"  Backend : {args.backend}")
    print(f"  Modelo  : {args.modelo}")
    print(f"  Casos   : {args.max_casos}")

    if args.backend == "airllm":
        libre = shutil.disk_usage(Path.home()).free / GB
        print(f"  Disco libre: {libre:.0f} GB (minimo exigido {args.disco_minimo_gb})")
        if libre < args.disco_minimo_gb:
            print(f"\n  ESPACIO INSUFICIENTE. AirLLM descompone el modelo por")
            print(f"  capas y necesita aproximadamente el tamano del modelo")
            print(f"  original en disco. Libera espacio o elige uno menor.\n")
            sys.exit(1)

    from src.agents.tools import construir_dossier_caso, inicializar_contexto, mapa_casos

    df = cargar_dataset()
    turno = construir_turno(df, horas=args.turno_horas,
                            desplazamiento_h=args.desplazamiento)
    detector = DetectorFraude()
    inicializar_contexto(turno, detector, capacidad=args.capacidad,
                         umbral=args.umbral)
    mapa = mapa_casos()
    n_total = len(mapa)
    n = min(args.max_casos, n_total)

    # Que casos investigar. El expediente va ordenado de mayor a menor
    # probabilidad, asi que la cabeza son los casos evidentes -que cualquier
    # modelo confirma- y la cola los ambiguos, donde se producen los descartes
    # y donde los modelos se diferencian. Validando el arnes con los diez
    # primeros salieron diez confirmaciones de diez, que es el resultado
    # correcto y a la vez completamente inutil para comparar motores.
    if args.zona == "cabeza":
        casos_n = list(range(1, n + 1))
    else:
        casos_n = list(range(n_total - n + 1, n_total + 1))

    print(f"\n  Turno: {len(turno):,} transacciones, "
          f"{int(turno[TARGET_COL].sum())} fraudes")
    print(f"  Expediente: {n_total} casos")
    print(f"  Se investigan {n} de la {args.zona}: casos "
          f"{casos_n[0]} a {casos_n[-1]}")
    if args.zona == "cabeza":
        print("  [AVISO] La cabeza no discrimina entre modelos: son los casos")
        print("  evidentes y todos los confirman. Usa --zona cola para comparar.")
    print()

    motor = (MotorAirLLM(args.modelo, args.compresion, args.hf_token)
             if args.backend == "airllm" else None)

    salidas, tiempos = [], []
    for i in casos_n:
        prompt = construir_prompt(i, construir_dossier_caso(i))
        t0 = time.perf_counter()
        if motor:
            texto = motor.generar(prompt, args.max_tokens)
        else:
            texto = generar_ollama(args.modelo, prompt, args.max_tokens)
        dt = time.perf_counter() - t0
        tiempos.append(dt)
        salidas.append(texto)

        v = veredictos_por_caso(texto).get(i, "sin veredicto")
        print(f"  [caso {i:>3}] {dt:>7.1f} s | {len(texto):>5} car. | {v}")

    texto_completo = "\n\n".join(salidas)

    # Se mide con la MISMA funcion que el sistema completo. El expediente se
    # recorta a los casos investigados para que las cifras sean coherentes.
    # El mapa se recorta a los casos investigados: medir sobre el expediente
    # completo contaria como "no descartados" casos que nadie llego a mirar.
    met = medir_sistema(turno, detector, texto_completo, "revisa",
                        capacidad=args.capacidad,
                        mapa_casos={k: mapa[k] for k in casos_n},
                        umbral=args.umbral)

    ver = veredictos_por_caso(texto_completo)
    print("\n" + "=" * 70)
    print("  RESULTADOS")
    print("=" * 70 + "\n")
    print(f"  Casos investigados      : {n}")
    print(f"  Con veredicto extraido  : {len(ver)}/{n}")
    if len(ver) < n:
        faltan = n - len(ver)
        print(f"\n  [AVISO] {faltan} caso(s) sin veredicto reconocible. Las")
        print("  metricas de abajo estan incompletas y NO son comparables con")
        print("  las del sistema completo. Revisa el formato de las salidas en")
        print("  el fichero de resultados antes de usarlas.\n")
    print(f"    confirmados           : {sum(1 for x in ver.values() if x=='CONFIRMADO')}")
    print(f"    descartados           : {sum(1 for x in ver.values() if x=='DESCARTADO')}")
    print(f"  Descartes acertados     : {met['n_descarte_correcto']}")
    print(f"  FRAUDE DESTRUIDO        : {met['n_fraude_descartado']}"
          + (f"  {met['fraude_descartado']}" if met['n_fraude_descartado'] else ""))
    print(f"\n  Tiempo por caso         : {sum(tiempos)/len(tiempos):.1f} s "
          f"(min {min(tiempos):.1f}, max {max(tiempos):.1f})")
    print(f"  Tiempo total            : {sum(tiempos)/60:.1f} min")
    if args.backend == "airllm":
        print(f"\n  Extrapolacion a un expediente de {n_total} casos: "
              f"{sum(tiempos)/len(tiempos)*n_total/60:.0f} min")

    sello = datetime.now().strftime("%Y%m%d_%H%M")
    destino = REPORTS_DIR / f"investigador_{args.backend}_{sello}.json"
    destino.write_text(json.dumps({
        "backend": args.backend, "modelo": args.modelo,
        "compresion": args.compresion if args.backend == "airllm" else None,
        "casos_investigados": n, "casos_expediente": n_total,
        "zona": args.zona, "casos": casos_n,
        "veredictos": {str(k): v for k, v in ver.items()},
        "descartes_correctos": met["n_descarte_correcto"],
        "fraude_destruido": met["n_fraude_descartado"],
        "seg_por_caso": [round(x, 1) for x in tiempos],
        "salidas": salidas,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")


if __name__ == "__main__":
    main()
