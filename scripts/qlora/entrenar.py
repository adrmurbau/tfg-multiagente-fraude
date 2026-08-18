"""
Ajuste fino QLoRA del Investigador - fase 16.

EJECUTAR EN EL ENTORNO .venv-airllm, nunca en el principal: necesita el
PyTorch con CUDA, y la pila de entrenamiento no debe tocar el entorno que
produjo los demas resultados.

    .\\.venv-airllm\\Scripts\\Activate.ps1
    pip install peft datasets trl
    python scripts\\qlora\\entrenar.py

## Que entrena

Un adaptador LoRA sobre Qwen2.5-14B-Instruct cuantizado a 4 bits, con los
pares (dossier, respuesta) de data/qlora/. El modelo base son ~9 GB en 4
bits; con lote de 1, acumulacion de 8 y secuencias de 1024 tokens cabe en los
16 GB de la RTX 5060 Ti. Si la memoria se agota, el primer ajuste es reducir
--max-len a 768.

## Que NO se toca

El modelo base. Solo el adaptador, que pesa unos 100-200 MB y se guarda en
models/qlora_dominio/. La evaluacion (evaluar.py) carga base + adaptador y
compara contra el base solo, con el mismo arnes de siempre.

Duracion estimada: 1-3 horas con los 540 ejemplos y 2 epocas. Pensado para
lanzarse de noche. Escribe metricas por paso en models/qlora_dominio/log.txt.
"""

import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DATOS = RAIZ / "data" / "qlora"
SALIDA = RAIZ / "models" / "qlora_dominio"

BASE = "Qwen/Qwen2.5-14B-Instruct"


def parsear_args():
    p = argparse.ArgumentParser(description="Ajuste QLoRA del Investigador")
    p.add_argument("--base", default=BASE)
    p.add_argument("--epocas", type=float, default=2.0)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--max-len", type=int, default=1024)
    p.add_argument("--lote", type=int, default=1)
    p.add_argument("--acumulacion", type=int, default=8)
    p.add_argument("--rango", type=int, default=16, help="Rango de LoRA.")
    return p.parse_args()


def comprobaciones_previas():
    """Todo lo que pueda fallar, que falle ANTES de descargar 9 GB.

    Leccion repetida tres veces en este proyecto: AirLLM descargo gigabytes
    antes de descubrir que torch no tenia CUDA, y luego que la GPU era mas
    nueva que la compilacion. La comprobacion barata va siempre delante del
    paso caro.
    """
    try:
        import torch
    except ImportError:
        sys.exit("Falta torch. Este guion va en el entorno .venv-airllm.")
    if not torch.cuda.is_available():
        sys.exit("PyTorch no ve la GPU. ¿Estas en .venv-airllm?")
    try:
        torch.zeros(4, 4, device="cuda") @ torch.zeros(4, 4, device="cuda")
        torch.cuda.synchronize()
    except Exception as e:
        sys.exit(f"La GPU no ejecuta nucleos con esta compilacion: {e}")

    for mod in ("transformers", "peft", "datasets", "bitsandbytes"):
        try:
            __import__(mod)
        except ImportError:
            sys.exit(f"Falta {mod}: pip install peft datasets transformers "
                     f"bitsandbytes")

    for f in ("train.jsonl", "val.jsonl"):
        if not (DATOS / f).exists():
            sys.exit(f"Falta {DATOS / f}. Ejecuta antes "
                     f"scripts/qlora/generar_dataset.py")

    import shutil
    libre = shutil.disk_usage(Path.home()).free / 1024**3
    if libre < 40:
        sys.exit(f"Solo {libre:.0f} GB libres; el modelo base necesita ~30.")

    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"  GPU: {torch.cuda.get_device_name(0)} ({vram:.0f} GB)  "
          f"disco libre {libre:.0f} GB  OK")


def main():
    args = parsear_args()
    print("=" * 70)
    print("  AJUSTE QLoRA DEL INVESTIGADOR")
    print("=" * 70)
    comprobaciones_previas()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig, Trainer, TrainingArguments)

    tk = AutoTokenizer.from_pretrained(args.base)
    if tk.pad_token is None:
        tk.pad_token = tk.eos_token

    print(f"  Cargando {args.base} en 4 bits (la primera vez descarga ~9 GB)")
    modelo = AutoModelForCausalLM.from_pretrained(
        args.base,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True),
        device_map={"": 0},
    )
    modelo = prepare_model_for_kbit_training(modelo)
    modelo = get_peft_model(modelo, LoraConfig(
        r=args.rango, lora_alpha=args.rango * 2, lora_dropout=0.05,
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"]))
    modelo.print_trainable_parameters()

    def preparar(ej):
        """Aplica la plantilla de conversacion y enmascara el prompt.

        La perdida se calcula SOLO sobre la respuesta. Sin la mascara, el
        modelo gastaria la mayor parte del gradiente en aprender a repetir el
        dossier, que ocupa cinco veces mas tokens que el veredicto.
        """
        prompt_ids = tk.apply_chat_template(
            [{"role": "user", "content": ej["prompt"]}],
            tokenize=True, add_generation_prompt=True)
        resp_ids = tk(ej["respuesta"] + tk.eos_token,
                      add_special_tokens=False)["input_ids"]
        ids = (prompt_ids + resp_ids)[:args.max_len]
        etiquetas = ([-100] * len(prompt_ids) + resp_ids)[:args.max_len]
        return {"input_ids": ids, "labels": etiquetas,
                "attention_mask": [1] * len(ids)}

    ds = load_dataset("json", data_files={
        "train": str(DATOS / "train.jsonl"),
        "val": str(DATOS / "val.jsonl")})
    ds = ds.map(preparar, remove_columns=ds["train"].column_names)

    def agrupar(lote):
        mayor = max(len(e["input_ids"]) for e in lote)
        import torch as T
        def rellenar(seq, valor):
            return seq + [valor] * (mayor - len(seq))
        return {
            "input_ids": T.tensor([rellenar(e["input_ids"], tk.pad_token_id) for e in lote]),
            "labels": T.tensor([rellenar(e["labels"], -100) for e in lote]),
            "attention_mask": T.tensor([rellenar(e["attention_mask"], 0) for e in lote]),
        }

    SALIDA.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    trainer = Trainer(
        model=modelo,
        args=TrainingArguments(
            output_dir=str(SALIDA / "checkpoints"),
            num_train_epochs=args.epocas,
            per_device_train_batch_size=args.lote,
            gradient_accumulation_steps=args.acumulacion,
            learning_rate=args.lr,
            lr_scheduler_type="cosine", warmup_ratio=0.05,
            logging_steps=5, logging_dir=str(SALIDA),
            eval_strategy="epoch", save_strategy="no",
            bf16=True, gradient_checkpointing=True,
            report_to=[],
        ),
        train_dataset=ds["train"], eval_dataset=ds["val"],
        data_collator=agrupar,
    )
    resultado = trainer.train()
    minutos = (time.perf_counter() - t0) / 60

    modelo.save_pretrained(str(SALIDA))
    tk.save_pretrained(str(SALIDA))
    (SALIDA / "entrenamiento.json").write_text(json.dumps({
        "base": args.base, "epocas": args.epocas, "lr": args.lr,
        "rango": args.rango, "max_len": args.max_len,
        "n_train": len(ds["train"]), "n_val": len(ds["val"]),
        "perdida_final": round(resultado.training_loss, 4),
        "minutos": round(minutos, 1),
    }, indent=2), encoding="utf-8")
    print(f"\n  Adaptador guardado en {SALIDA}")
    print(f"  Perdida final {resultado.training_loss:.4f} en {minutos:.0f} min")
    print("  Siguiente paso: python scripts\\qlora\\evaluar.py")


if __name__ == "__main__":
    main()
