"""
El Investigador sobre un caso del dataset Sparkov (extension exploratoria).

Mismo backend y misma logica de extraccion de veredicto que
scripts/investigador_solo.py, pero con un expediente de variables de negocio
en lugar del expediente PCA del sistema principal. La pregunta que responde:
con comercio, categoria, distancia y edad disponibles, ¿el parrafo del
investigador cambia de naturaleza, o sigue limitandose a leer el importe como
en el caso 55 del dataset principal (5.11)?

Requiere Ollama corriendo en local (igual que el resto del sistema). No se
ejecuta desde el entorno de desarrollo de la memoria porque ese entorno no
tiene acceso a la GPU del usuario.

Uso:
    python scripts\\sparkov\\investigar_caso.py --modelo qwen2.5-14b-ctx16k
    python scripts\\sparkov\\investigar_caso.py --modelo qwen2.5-14b-ctx16k --caso 2
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import OLLAMA_HOST  # noqa: E402

REPORTES = Path(__file__).resolve().parent.parent.parent / "reports"

IDIOMA = (
    " Redactas SIEMPRE en castellano, incluidos titulos, etiquetas y "
    "conclusiones, sea cual sea el idioma del contexto que recibas. Los "
    "importes de este expediente estan en DOLARES (USD): es un dataset "
    "simulado con datos demograficos y geograficos estadounidenses, y "
    "convertirlos a otra moneda inventaria un dato que no esta en el "
    "expediente."
)

AVISO_SINTETICO = (
    "\nAVISO: este expediente procede de un generador de datos SINTETICOS "
    "(Sparkov), no de transacciones reales. Los nombres de comercio, "
    "titulares y ubicaciones son ficticios. Razona sobre las variables "
    "disponibles con la misma seriedad que si fueran reales; no comentes "
    "que son sinteticos en tu respuesta, limitate a explicar el caso.\n"
)


def construir_dossier(caso: dict, n: int) -> str:
    contrib = "\n".join(
        f"  {var}: {val:+.3f}" for var, val in caso["contribuciones"]
    )
    return (
        f"CASO {n}\n"
        f"Comercio: {caso['comercio']}\n"
        f"Categoria de comercio: {caso['categoria']}\n"
        f"Importe: {caso['importe']:.2f} USD\n"
        f"Hora del dia: {caso['hora']:.1f} h\n"
        f"Edad del titular: {caso['edad']:.0f} anios\n"
        f"Distancia domicilio-comercio: {caso['distancia_km']:.1f} km\n"
        f"Poblacion de la ciudad del titular: {caso['poblacion_ciudad']:,}\n"
        f"Probabilidad de fraude segun el detector: {caso['probabilidad']:.4f}\n"
        f"Contribuciones principales del detector (Shapley, XGBoost):\n{contrib}"
    )


def construir_prompt(n: int, dossier: str) -> str:
    veredicto = (
        "Para el caso emite ademas un veredicto: CONFIRMADO si las "
        "evidencias respaldan la sospecha, o DESCARTADO si crees que es un "
        "falso positivo. Se conservador: descartar un fraude real es mucho "
        "mas caro que revisar de mas. Escribe el veredicto en MAYUSCULAS al "
        "final, en una linea aparte."
    )
    salida_esperada = (
        f"La linea 'CASO {n}' seguida de un parrafo explicativo en prosa. "
        f"Termina con una linea 'VEREDICTO: CONFIRMADO' o "
        f"'VEREDICTO: DESCARTADO'."
    )
    return (
        "Eres un investigador de fraude. Explicas por que el detector "
        "considera sospechosa cada transaccion." + IDIOMA + "\n\n"
        + AVISO_SINTETICO + "\n"
        f"{dossier}\n\n"
        f"Redacta UN SOLO parrafo de 3 a 5 frases explicando en lenguaje "
        f"llano por que el detector considera sospechoso el CASO {n}. "
        f"Menciona el comercio, la categoria y las variables de mayor "
        f"aporte tal y como aparecen arriba.\n"
        f"FORMATO: empieza con la linea 'CASO {n}' y debajo el parrafo en "
        f"prosa. Sin tablas ni vinetas.\n"
        + veredicto
        + f"\n\nEsto es lo que se espera de tu respuesta: {salida_esperada}"
    )


def generar_ollama(modelo: str, prompt: str, max_tokens: int) -> str:
    import requests
    r = requests.post(
        f"{OLLAMA_HOST.rstrip('/')}/api/generate",
        json={"model": modelo, "prompt": prompt, "stream": False,
              "options": {"num_predict": max_tokens, "temperature": 0.1}},
        timeout=1800,
    )
    r.raise_for_status()
    d = r.json()
    texto = (d.get("response") or "").strip()
    if not texto:
        pensado = (d.get("thinking") or "").strip()
        if pensado:
            print(f"  [AVISO] respuesta vacia: {len(pensado)} caracteres de "
                  f"pensamiento. Sube --max-tokens.")
        else:
            print(f"  [AVISO] respuesta vacia. done_reason="
                  f"{d.get('done_reason', 'desconocido')}")
    return texto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="qwen2.5-14b-ctx16k")
    ap.add_argument("--caso", type=int, default=None,
                     help="indice del ejemplo en sparkov_metricas.json (por defecto, todos)")
    ap.add_argument("--max-tokens", type=int, default=280)
    args = ap.parse_args()

    ruta = REPORTES / "sparkov_metricas.json"
    if not ruta.exists():
        print(f"No existe {ruta}. Ejecuta antes:\n"
              f"  python scripts\\sparkov\\entrenar_detector.py")
        sys.exit(1)

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    ejemplos = datos["ejemplos_contribuciones"]
    indices = [args.caso] if args.caso is not None else list(range(len(ejemplos)))

    resultados = []
    for i in indices:
        caso = ejemplos[i]
        dossier = construir_dossier(caso, i + 1)
        prompt = construir_prompt(i + 1, dossier)
        print(f"\n{'=' * 66}\n  CASO {i + 1}: {caso['comercio']} | {caso['categoria']} | "
              f"{caso['importe']:.2f} USD\n{'=' * 66}")
        print(dossier)
        print(f"\n  --- respuesta de {args.modelo} ---")
        respuesta = generar_ollama(args.modelo, prompt, args.max_tokens)
        print(respuesta)

        m = re.search(r"VEREDICTO:\s*(CONFIRMADO|DESCARTADO)", respuesta, re.IGNORECASE)
        veredicto = m.group(1).upper() if m else "SIN VEREDICTO"
        resultados.append({"caso": i + 1, "comercio": caso["comercio"],
                            "categoria": caso["categoria"], "importe": caso["importe"],
                            "respuesta": respuesta, "veredicto": veredicto})

    salida = REPORTES / f"sparkov_investigacion_{args.modelo.replace(':', '-')}.json"
    salida.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n\nGuardado -> {salida}")
    print("\nRecuerda: todos estos casos son FRAUDE REAL (se seleccionaron por "
          "es_fraude=1 en el conjunto de prueba). Un DESCARTADO es un fraude perdido.")


if __name__ == "__main__":
    main()
