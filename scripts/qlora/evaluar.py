"""
Evaluacion del adaptador QLoRA - fase 16.

EJECUTAR EN .venv-airllm. Compara, sobre los MISMOS casos y con el MISMO
prompt del arnes, tres condiciones:

    base            el modelo sin tocar
    base+dominio    el modelo con la correccion en el enunciado (referencia
                    de 5.12: cambia la prosa, no el veredicto)
    adaptado        el modelo con el adaptador QLoRA, SIN correccion en el
                    enunciado

La pregunta es si el adaptador logra lo que el enunciado no logro: salvar los
fraudes de la cola (casos 50 y 55, identificadores 12377 y 1885) sin volcarse
a confirmar todo, que es el modo de fallo que mostro el 8B con la correccion.
Los casos 53 y 54 son el control de ese vuelco.

La generacion va por transformers, no por Ollama: el adaptador no se puede
cargar en Ollama sin fusionarlo y convertirlo, y esa conversion introduciria
una variable mas. El coste es que el modelo en 4 bits por transformers genera
mas despacio; con 12 casos por condicion es asumible.

Uso:
    python scripts/qlora/evaluar.py
    python scripts/qlora/evaluar.py --casos 50,53,54,55
"""

import argparse
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from src.config import REPORTS_DIR, TARGET_COL  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_turno  # noqa: E402
from src.evaluacion import veredictos_por_caso  # noqa: E402

ADAPTADOR = RAIZ / "models" / "qlora_dominio"


def parsear_args():
    p = argparse.ArgumentParser(description="Evaluacion del adaptador QLoRA")
    p.add_argument("--base", default="Qwen/Qwen2.5-14B-Instruct")
    p.add_argument("--casos", default="44,45,46,47,48,49,50,51,52,53,54,55",
                   help="Cola completa por defecto, para comparar con las "
                        "tandas del arnes.")
    p.add_argument("--umbral", type=float, default=0.05)
    p.add_argument("--max-tokens", type=int, default=220)
    p.add_argument("--condiciones", nargs="+",
                   default=["base", "base+dominio", "adaptado"])
    return p.parse_args()


def cargar_generador(base, con_adaptador):
    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)
    tk = AutoTokenizer.from_pretrained(base)
    m = AutoModelForCausalLM.from_pretrained(
        base,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True),
        device_map={"": 0},
    )
    if con_adaptador:
        from peft import PeftModel
        if not (ADAPTADOR / "adapter_config.json").exists():
            sys.exit(f"No hay adaptador en {ADAPTADOR}. Entrena primero.")
        m = PeftModel.from_pretrained(m, str(ADAPTADOR))
    m.eval()

    def generar(prompt, max_tokens):
        entrada = tk.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=True, add_generation_prompt=True, return_tensors="pt",
        )
        # Segun la version de transformers, esto devuelve un tensor plano o
        # un BatchEncoding; se normaliza a tensor antes de pasarlo a generate,
        # que espera input_ids como primer argumento posicional, no un dict.
        if not torch.is_tensor(entrada):
            entrada = entrada["input_ids"]
        entrada = entrada.to(m.device)
        with torch.no_grad():
            salida = m.generate(
                entrada, max_new_tokens=max_tokens, do_sample=False,
                temperature=None, top_p=None,
                pad_token_id=tk.pad_token_id or tk.eos_token_id)
        return tk.decode(salida[0][entrada.shape[1]:],
                         skip_special_tokens=True).strip()
    return generar


def main():
    args = parsear_args()
    casos_n = sorted(int(x) for x in args.casos.replace(" ", "").split(","))

    print("=" * 70)
    print("  EVALUACION DEL ADAPTADOR QLoRA")
    print("=" * 70)

    # El expediente, identico al del arnes.
    from src.agents.tools import construir_dossier_caso, inicializar_contexto, mapa_casos
    df = cargar_dataset()
    turno = construir_turno(df, horas=4.0, desplazamiento_h=0.0)
    det = DetectorFraude()
    inicializar_contexto(turno, det, capacidad=60, umbral=args.umbral, minimo=0)
    mapa = mapa_casos()
    reales = {n: bool(turno.loc[mapa[n], TARGET_COL] == 1) for n in casos_n}
    print(f"  Casos: {casos_n}")
    print(f"  Fraudes reales entre ellos: {[n for n in casos_n if reales[n]]}\n")

    ruta = RAIZ / "scripts" / "investigador_solo.py"
    spec = importlib.util.spec_from_file_location("inv_solo", ruta)
    arnes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(arnes)

    resultados = {}
    for cond in args.condiciones:
        con_adapt = cond == "adaptado"
        con_dominio = cond == "base+dominio"
        print(f"  --- condicion: {cond} ---")
        gen = cargar_generador(args.base, con_adapt)
        veredictos, tiempos, salidas = {}, [], {}
        for n in casos_n:
            prompt = arnes.construir_prompt(n, construir_dossier_caso(n),
                                            con_dominio)
            t0 = time.perf_counter()
            texto = gen(prompt, args.max_tokens)
            dt = time.perf_counter() - t0
            tiempos.append(dt)
            salidas[n] = texto
            v = veredictos_por_caso(texto).get(n)
            if v:
                veredictos[n] = v
            marca = ""
            if v == "DESCARTADO" and reales[n]:
                marca = "  <-- FRAUDE DESTRUIDO"
            elif v == "CONFIRMADO" and reales[n]:
                marca = "  <-- fraude salvado"
            print(f"    [caso {n:>3}] {dt:>6.1f} s | {v or 'sin veredicto'}{marca}")

        destr = [n for n, v in veredictos.items() if v == "DESCARTADO" and reales[n]]
        conf = sum(1 for v in veredictos.values() if v == "CONFIRMADO")
        resultados[cond] = {
            "veredictos": {str(k): v for k, v in veredictos.items()},
            "extraidos": len(veredictos), "confirmados": conf,
            "fraude_destruido": len(destr), "ids_destruidos": destr,
            "seg_por_caso": round(sum(tiempos) / len(tiempos), 1),
            "salidas": salidas,
        }
        # Liberar la GPU entre condiciones.
        del gen
        import torch, gc
        gc.collect(); torch.cuda.empty_cache()
        print()

    print("=" * 70)
    print("  RESUMEN")
    print("=" * 70)
    print(f"\n  {'condicion':<15}{'extraidos':>10}{'confirmados':>13}"
          f"{'destruido':>11}{'s/caso':>8}")
    print("  " + "-" * 57)
    for cond, r in resultados.items():
        print(f"  {cond:<15}{r['extraidos']:>7}/{len(casos_n):<2}"
              f"{r['confirmados']:>13}{r['fraude_destruido']:>11}"
              f"{r['seg_por_caso']:>8}")

    print("\n  Lectura: el adaptado debe compararse en DOS ejes a la vez.")
    print("  Salvar los fraudes 50 y 55 solo cuenta si los controles 53 y 54")
    print("  siguen descartados; confirmar todo es el vuelco del 8B, no una")
    print("  mejora. Con doce casos no hay contraste estadistico: es una")
    print("  demostracion y asi debe reportarse.")

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = REPORTS_DIR / f"qlora_eval_{marca}.json"
    destino.write_text(json.dumps({
        "base": args.base, "casos": casos_n,
        "reales": {str(k): v for k, v in reales.items()},
        "max_tokens": args.max_tokens,
        "resultados": resultados,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")


if __name__ == "__main__":
    main()
