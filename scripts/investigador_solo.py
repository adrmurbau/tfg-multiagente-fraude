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
import re
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
    p.add_argument("--casos", default=None,
                   help="Numeros de caso concretos, separados por comas, en "
                        "lugar de una zona. A 2,5 h por caso con AirLLM no se "
                        "puede recorrer el expediente entero, y la mayoria de "
                        "la cola son legitimas que todo modelo descarta y que "
                        "por tanto no distinguen nada. Dirigir la ejecucion a "
                        "los casos que SI son fraude cuesta lo mismo y "
                        "responde a la pregunta. Debe declararse como seleccion "
                        "deliberada al informar: la cifra resultante ya no es "
                        "una tasa sobre la cola sino la respuesta a si el "
                        "modelo salva esos casos concretos.")
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
    from src.agents.prompts import IDIOMA, PROHIBICIONES

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

    # Tope de tokens de entrada. El valor de 2048 de la primera version era
    # arbitrario y recortaba el dossier en silencio.
    MAX_ENTRADA = 8192

    def __init__(self, repo: str, compresion: str = "4bit", hf_token: str = None):
        try:
            from airllm import AutoModel
        except ImportError:
            print("\n  Falta airllm. Instalalo con:\n      pip install airllm\n")
            sys.exit(1)

        # Comprobacion previa de la GPU. AirLLM descarga el modelo ANTES de
        # tocarla, de modo que un PyTorch inservible no se manifiesta hasta
        # haber bajado gigabytes.
        #
        # No basta con torch.cuda.is_available(). Con una RTX 5060 Ti
        # -Blackwell, sm_120- las ruedas de cu121 devuelven True, dan el nombre
        # correcto de la tarjeta y fallan luego al lanzar cualquier nucleo,
        # porque no traen codigo compilado para esa capacidad. La unica
        # comprobacion fiable es ejecutar una operacion de verdad.
        try:
            import torch
        except ImportError:
            print("\n  Falta PyTorch.\n")
            sys.exit(1)

        problema = None
        if not torch.cuda.is_available():
            problema = "PyTorch no ve ninguna GPU"
        else:
            try:
                torch.zeros(8, 8, device="cuda") @ torch.zeros(8, 8, device="cuda")
                torch.cuda.synchronize()
            except Exception as e:
                cap = "%d%d" % torch.cuda.get_device_capability(0)
                problema = (f"la GPU es sm_{cap} y esta compilacion solo trae "
                            f"{' '.join(torch.cuda.get_arch_list())}\n"
                            f"    ({type(e).__name__}: {str(e)[:90]})")

        if problema:
            print(f"\n  PyTorch {torch.__version__} no puede usar la GPU:")
            print(f"    {problema}\n")
            print("  Instala la rueda que corresponda a la tarjeta. Para las")
            print("  Blackwell (serie RTX 50) hace falta CUDA 12.8:\n")
            print("      pip install --force-reinstall torch --index-url "
                  "https://download.pytorch.org/whl/cu128\n")
            print("  Conviene hacerlo en un entorno APARTE del principal, para")
            print("  no sustituir el PyTorch del que dependen los demas")
            print("  resultados del trabajo.\n")
            sys.exit(1)

        print(f"  GPU: {torch.cuda.get_device_name(0)} "
              f"({torch.cuda.get_device_properties(0).total_memory / GB:.0f} GB, "
              f"sm_%d%d)" % torch.cuda.get_device_capability(0))

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
        """Genera la respuesta, aplicando la plantilla de conversacion.

        La plantilla NO es un adorno. Qwen2.5-72B-Instruct espera sus marcas
        <|im_start|> y <|im_end|>; sin ellas no interpreta el texto como una
        peticion sino como un documento que hay que continuar.

        La primera version pasaba el prompt en crudo. Las respuestas salian en
        castellano y con sentido -de ahi que pareciesen validas- pero empezaban
        rematando la ultima frase de las instrucciones, "Nada mas.", "No
        escribas nada mas.", y despues se repetian, porque nada marcaba el
        final. Ollama aplica la plantilla por su cuenta, asi que omitirla aqui
        comparaba dos regimenes distintos y no dos modelos.
        """
        tk = self.modelo.tokenizer
        if getattr(tk, "chat_template", None):
            entrada = tk.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False, add_generation_prompt=True)
        else:
            print("  [AVISO] El tokenizador no trae plantilla de conversacion. "
                  "Se envia el prompt en crudo y el resultado NO es comparable "
                  "con los de Ollama.")
            entrada = prompt

        tok = tk([entrada], return_tensors="pt", truncation=True,
                 max_length=self.MAX_ENTRADA, padding=False)
        n_entrada = tok["input_ids"].shape[1]
        if n_entrada >= self.MAX_ENTRADA:
            print(f"  [AVISO] La entrada alcanzo el tope de {self.MAX_ENTRADA} "
                  "tokens y se ha recortado: el modelo no ha visto el dossier "
                  "completo.")

        gen = dict(max_new_tokens=max_tokens, use_cache=True,
                   return_dict_in_generate=True)
        # Sin eos_token_id el modelo agota siempre los max_new_tokens. A 42
        # segundos por token eso no es solo lento: es lo que producia la
        # repeticion que rompia la extraccion de veredictos.
        if tk.eos_token_id is not None:
            gen["eos_token_id"] = tk.eos_token_id
            gen["pad_token_id"] = tk.pad_token_id or tk.eos_token_id
        if "attention_mask" in tok:
            gen["attention_mask"] = tok["attention_mask"].cuda()

        salida = self.modelo.generate(tok["input_ids"].cuda(), **gen)
        # Se decodifican SOLO los tokens nuevos. Recortar por longitud de
        # cadena fallaba en cuanto la plantilla anadia marcas al principio.
        return tk.decode(salida.sequences[0][n_entrada:],
                         skip_special_tokens=True).strip()


def recortar_en_veredicto(texto: str) -> str:
    """Devuelve el texto hasta el final de su primer veredicto.

    Los modelos tienden a seguir escribiendo despues de haber contestado:
    repiten el caso, abren una cabecera 'CASO n' que ya no cierran, inventan
    un encabezado de correo. Ese arrastre es inofensivo leido de uno en uno,
    pero al concatenar varias salidas convierte la cabecera huerfana de una en
    el prefijo del veredicto de la siguiente.

    Recortar en el veredicto no descarta informacion util: todo lo que va
    despues es, por construccion, posterior a la respuesta pedida.
    """
    m = re.search(r"(?:VEREDICTO|VERDICT):\s*"
                  r"(?:CONFIRMADO|DESCARTADO|CONFIRMED|DISCARDED|DISMISSED)",
                  texto, re.IGNORECASE)
    return texto[:m.end()] if m else texto


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
    if args.casos:
        casos_n = sorted(int(x) for x in args.casos.replace(" ", "").split(","))
        fuera = [c for c in casos_n if c not in mapa]
        if fuera:
            print(f"\n  Los casos {fuera} no existen: el expediente tiene "
                  f"{n_total}.\n")
            sys.exit(1)
        n = len(casos_n)
    elif args.zona == "cabeza":
        casos_n = list(range(1, n + 1))
    else:
        casos_n = list(range(n_total - n + 1, n_total + 1))

    print(f"\n  Turno: {len(turno):,} transacciones, "
          f"{int(turno[TARGET_COL].sum())} fraudes")
    print(f"  Expediente: {n_total} casos")
    if args.casos:
        print(f"  Se investigan {n} casos elegidos: "
              f"{', '.join(str(c) for c in casos_n)}")
        print("  [NOTA] Seleccion deliberada, no una zona. Al informar la cifra")
        print("  debe decirse cuales se eligieron y por que.")
    else:
        print(f"  Se investigan {n} de la {args.zona}: casos "
              f"{casos_n[0]} a {casos_n[-1]}")
    if args.zona == "cabeza" and not args.casos:
        print("  [AVISO] La cabeza no discrimina entre modelos: son los casos")
        print("  evidentes y todos los confirman. Usa --zona cola para comparar.")
    print()

    motor = (MotorAirLLM(args.modelo, args.compresion, args.hf_token)
             if args.backend == "airllm" else None)

    salidas, tiempos, ver = [], [], {}
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

        # El veredicto se extrae de CADA salida por separado, que es como se
        # genero. Agregarlo concatenando las tres y analizando el resultado
        # perdia veredictos: si una salida termina con una cabecera 'CASO n'
        # colgante -algo habitual cuando el modelo se repite-, la expresion
        # regular la empareja con el VEREDICTO de la salida SIGUIENTE, y el
        # ultimo caso se queda sin ninguno. Ocurrio con AirLLM: los tres casos
        # llevaban su veredicto y el recuento dijo 2 de 3.
        v = veredictos_por_caso(texto).get(i)
        if v:
            ver[i] = v
        print(f"  [caso {i:>3}] {dt:>7.1f} s | {len(texto):>5} car. | "
              f"{v or 'sin veredicto'}")

    # Para medir se concatenan las salidas RECORTADAS en su veredicto, de modo
    # que ninguna cabecera colgante contamine a la siguiente. medir_sistema
    # vuelve a analizar el texto por su cuenta y sufriria el mismo problema.
    texto_completo = "\n\n".join(recortar_en_veredicto(s) for s in salidas)

    # Se mide con la MISMA funcion que el sistema completo. El expediente se
    # recorta a los casos investigados para que las cifras sean coherentes.
    # El mapa se recorta a los casos investigados: medir sobre el expediente
    # completo contaria como "no descartados" casos que nadie llego a mirar.
    met = medir_sistema(turno, detector, texto_completo, "revisa",
                        capacidad=args.capacidad,
                        mapa_casos={k: mapa[k] for k in casos_n},
                        umbral=args.umbral)

    # ver ya se acumulo caso a caso en el bucle; no se recalcula aqui.
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
