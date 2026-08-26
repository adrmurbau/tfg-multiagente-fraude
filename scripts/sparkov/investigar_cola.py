"""
Investigador sobre la cola de Sparkov, completo vs reducido.

Ejecuta el mismo caso dos veces -dossier completo (comercio, categoria, edad,
distancia, poblacion con sus nombres reales) y dossier reducido (las mismas
variables anonimizadas como var_N, solo importe y hora con nombre, igual que
el techo de legibilidad del dataset ULB)- y compara el veredicto. Es la unica
diferencia entre ambas ejecuciones: mismo caso, mismo detector, mismas
contribuciones numericas.

Requiere reports/sparkov_cola.json (generado por generar_cola.py) y Ollama en
local.

Uso:
    python scripts\\sparkov\\investigar_cola.py --modelo qwen2.5-14b-ctx16k
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
    "simulado con datos demograficos y geograficos estadounidenses."
)

AVISO_SINTETICO = (
    "\nAVISO: este expediente procede de un generador de datos SINTETICOS "
    "(Sparkov), no de transacciones reales. Los nombres de comercio, "
    "titulares y ubicaciones son ficticios cuando aparecen. Razona sobre las "
    "variables disponibles con la misma seriedad que si fueran reales; no "
    "comentes que son sinteticas en tu respuesta, limitate a explicar el "
    "caso.\n"
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
        f"Menciona las variables disponibles y su aporte tal y como "
        f"aparecen arriba.\n"
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


def veredicto_de(texto: str) -> str:
    m = re.search(r"VEREDICTO:\s*(CONFIRMADO|DESCARTADO)", texto, re.IGNORECASE)
    return m.group(1).upper() if m else "SIN VEREDICTO"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="qwen2.5-14b-ctx16k")
    ap.add_argument("--max-tokens", type=int, default=280)
    args = ap.parse_args()

    ruta = REPORTES / "sparkov_cola.json"
    if not ruta.exists():
        print(f"No existe {ruta}. Ejecuta antes:\n"
              f"  python scripts\\sparkov\\generar_cola.py")
        sys.exit(1)

    casos = json.loads(ruta.read_text(encoding="utf-8"))["casos"]

    resultados = []
    for caso in casos:
        n = caso["n"]
        real = "FRAUDE" if caso["es_fraude"] else "legitima"
        print(f"\n{'=' * 70}\n  CASO {n} [{real}]: {caso['comercio']} | "
              f"{caso['categoria']} | {caso['importe']:.2f} USD | "
              f"p={caso['probabilidad']:.4f}\n{'=' * 70}")

        fila = {"completo": {}, "reducido": {}}
        for cond, dossier in [("completo", caso["dossier_completo"]),
                               ("reducido", caso["dossier_reducido"])]:
            prompt = construir_prompt(n, dossier)
            print(f"\n  --- {cond} ---")
            respuesta = generar_ollama(args.modelo, prompt, args.max_tokens)
            v = veredicto_de(respuesta)
            print(respuesta)
            print(f"  [veredicto: {v}]")
            fila[cond] = {"respuesta": respuesta, "veredicto": v}

        marca = ""
        if fila["completo"]["veredicto"] != fila["reducido"]["veredicto"]:
            marca = "  <-- CAMBIA EL VEREDICTO ENTRE VERSIONES"
        print(f"\n  completo={fila['completo']['veredicto']}  "
              f"reducido={fila['reducido']['veredicto']}{marca}")

        resultados.append({
            "n": n, "es_fraude": caso["es_fraude"], "comercio": caso["comercio"],
            "categoria": caso["categoria"], "importe": caso["importe"],
            "probabilidad": caso["probabilidad"],
            "completo": fila["completo"], "reducido": fila["reducido"],
        })

    print(f"\n\n{'=' * 70}\n  RESUMEN\n{'=' * 70}")
    print(f"\n  {'caso':<6}{'real':<10}{'completo':<14}{'reducido':<14}{'cambia'}")
    for r in resultados:
        cambia = "SI" if r["completo"]["veredicto"] != r["reducido"]["veredicto"] else ""
        real = "FRAUDE" if r["es_fraude"] else "legitima"
        print(f"  {r['n']:<6}{real:<10}{r['completo']['veredicto']:<14}"
              f"{r['reducido']['veredicto']:<14}{cambia}")

    fraude_salvado_completo = sum(1 for r in resultados if r["es_fraude"]
                                   and r["completo"]["veredicto"] == "CONFIRMADO")
    fraude_salvado_reducido = sum(1 for r in resultados if r["es_fraude"]
                                   and r["reducido"]["veredicto"] == "CONFIRMADO")
    controles_bien_completo = sum(1 for r in resultados if not r["es_fraude"]
                                   and r["completo"]["veredicto"] == "DESCARTADO")
    controles_bien_reducido = sum(1 for r in resultados if not r["es_fraude"]
                                   and r["reducido"]["veredicto"] == "DESCARTADO")
    print(f"\n  Fraude confirmado -- completo: {fraude_salvado_completo}  "
          f"reducido: {fraude_salvado_reducido}")
    print(f"  Controles descartados bien -- completo: {controles_bien_completo}  "
          f"reducido: {controles_bien_reducido}")

    salida = REPORTES / f"sparkov_cola_{args.modelo.replace(':', '-')}.json"
    salida.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Guardado -> {salida}")


if __name__ == "__main__":
    main()
