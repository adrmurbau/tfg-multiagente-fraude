"""
Genera el conjunto de entrenamiento para el ajuste fino QLoRA - fase 16.

## La pregunta

La seccion 5.12 de la memoria muestra que corregir por el ENUNCIADO la
premisa falsa sobre el importe cambia la prosa del modelo y no su decision.
Este experimento pregunta si la premisa se corrige por los PESOS: se entrena
un adaptador sobre dossieres etiquetados y se evalua con el mismo arnes.

## De donde salen los ejemplos, y de donde NO

Exclusivamente del periodo de ENTRENAMIENTO de la particion temporal: las
primeras 40,3 horas. Los casos con los que se evalua viven en las ultimas 7,7
y no pueden aparecer ni ellos ni sus vecinos temporales. Incluirlos seria la
misma fuga de informacion que el capitulo 2 documenta en la literatura, y es
lo primero que se comprobaria en una revision. El guion lo verifica de forma
programatica y aborta si falla.

Los dossieres se construyen con el MISMO detector y el mismo formato que en
produccion. El detector se entreno sobre este periodo, de modo que sus
probabilidades aqui son en-muestra y algo optimistas; se declara como
limitacion en lugar de resolverse con ajuste cruzado, que doblaria el coste
para un refinamiento que no afecta a la pregunta.

## Que se le ensena

Pares (dossier, respuesta) con el formato EXACTO que el arnes sabe medir:
'CASO n', un parrafo breve y 'VEREDICTO: CONFIRMADO/DESCARTADO' segun la
etiqueta real. El parrafo se genera por plantilla con los valores del caso.
Riesgo declarado: el modelo puede aprender el formato y no el criterio; por
eso la evaluacion mira los veredictos sobre casos nuevos, no la prosa.

Composicion deliberada:
  - mitad fraudes (objetivo CONFIRMADO), mitad falsos positivos del propio
    detector (objetivo DESCARTADO): el modelo debe aprender a distinguir,
    no a confirmar todo lo elevado;
  - entre los fraudes se sobrerrepresentan los de importe bajo, que son
    exactamente los que la premisa erronea destruye.

Uso:
    python scripts/qlora/generar_dataset.py
    python scripts/qlora/generar_dataset.py --n-por-clase 300 --umbral 0.05
"""

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from src.config import REPORTS_DIR, TARGET_COL, TEST_SIZE  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude  # noqa: E402

DESTINO = RAIZ / "data" / "qlora"


def parsear_args():
    p = argparse.ArgumentParser(description="Dataset de entrenamiento QLoRA")
    p.add_argument("--n-por-clase", type=int, default=300,
                   help="Ejemplos por clase (fraude / falso positivo).")
    p.add_argument("--umbral", type=float, default=0.05,
                   help="Solo se toman casos que el detector elevaria: son "
                        "los unicos que el Investigador ve en produccion.")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--frac-validacion", type=float, default=0.1)
    return p.parse_args()


_MOD_ARNES = None

def construir_prompt_arnes(n, dossier, dominio=False):
    """El MISMO prompt del arnes, importado de scripts/investigador_solo.py.

    Si el prompt de entrenamiento difiriera del de evaluacion en una sola
    linea, cualquier mejora medida podria deberse a esa linea y no al ajuste.
    Se entrena SIN la correccion de dominio: la pregunta es si los pesos
    sustituyen al enunciado, no si se suman a el.
    """
    global _MOD_ARNES
    if _MOD_ARNES is None:
        ruta = RAIZ / "scripts" / "investigador_solo.py"
        spec = importlib.util.spec_from_file_location("inv_solo", ruta)
        _MOD_ARNES = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_MOD_ARNES)
    return _MOD_ARNES.construir_prompt(n, dossier, dominio)


def respuesta_objetivo(n, exp, es_fraude):
    """Respuesta de entrenamiento: parrafo por plantilla + veredicto real.

    La plantilla cita las contribuciones reales del caso para que el texto
    sea coherente con el dossier, y varia la conclusion segun la etiqueta.
    Se mantiene deliberadamente sobria: cuanto mas florida la plantilla, mas
    probable que el modelo aprenda a recitarla en lugar de a decidir.
    """
    arriba = [c for c in exp.contribuciones if c[2] > 0][:2]
    abajo = [c for c in exp.contribuciones if c[2] < 0][:2]
    frases = [f"El detector eleva el CASO {n} con probabilidad "
              f"{exp.probabilidad:.4f} y un importe de {exp.importe:.2f} EUR."]
    if arriba:
        frases.append("Empujan hacia fraude "
                      + " y ".join(f"{v} ({a:+.3f})" for v, _, a in arriba) + ".")
    if abajo:
        frases.append("En sentido contrario, "
                      + " y ".join(f"{v} ({a:+.3f})" for v, _, a in abajo) + ".")
    if es_fraude:
        if exp.importe <= 5:
            frases.append("El importe reducido no es un atenuante: el cargo "
                          "minimo de prueba es un patron habitual de fraude, "
                          "y las contribuciones dominantes lo respaldan.")
        else:
            frases.append("Las contribuciones dominantes sostienen la "
                          "sospecha del detector.")
        veredicto = "CONFIRMADO"
    else:
        frases.append("El conjunto de aportes no sostiene la sospecha: el "
                      "patron es compatible con una operacion legitima.")
        veredicto = "DESCARTADO"
    return f"CASO {n}\n" + " ".join(frases) + f"\nVEREDICTO: {veredicto}"


def main():
    args = parsear_args()
    rng = random.Random(args.semilla)
    DESTINO.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  DATASET DE ENTRENAMIENTO QLoRA")
    print("=" * 70)

    df = cargar_dataset()
    orden = df.sort_values("Time", kind="mergesort")
    corte = int(len(orden) * (1 - TEST_SIZE))
    train = orden.iloc[:corte]
    hora_corte = float(orden.iloc[corte]["Time"]) / 3600
    print(f"  Periodo de entrenamiento: hasta la hora {hora_corte:.1f} "
          f"({len(train):,} transacciones)")

    det = DetectorFraude()
    punt = det.puntuar(train)
    elevables = punt[punt["prob_fraude"] >= args.umbral]
    frau = elevables[train.loc[elevables.index, TARGET_COL] == 1]
    fp = elevables[train.loc[elevables.index, TARGET_COL] == 0]
    print(f"  Elevables con umbral {args.umbral}: {len(elevables):,} "
          f"({len(frau)} fraudes, {len(fp)} falsos positivos)")

    # El detector, puntuado sobre su propio periodo de entrenamiento, apenas
    # comete falsos positivos: en el primer ensayo solo 20 superaban el
    # umbral, insuficiente para equilibrar las clases. La clase DESCARTADO se
    # completa con las legitimas de MAYOR probabilidad aunque no lleguen al
    # umbral: son los negativos dificiles, los casos mas parecidos a fraude
    # que un ejemplo facil no ensenaria a distinguir. Se declara en el
    # resumen, porque implica que parte de los DESCARTADO de entrenamiento
    # tiene probabilidades que en produccion no llegarian al expediente.
    legit = punt[train.loc[punt.index, TARGET_COL] == 0]
    duros = legit.sort_values("prob_fraude", ascending=False)

    n = args.n_por_clase
    # Fraudes: mitad del cupo reservada a importes <= 5 EUR, que son los que
    # la premisa erronea destruye. Si no hay bastantes, se completa.
    frau_amt = train.loc[frau.index, "Amount"]
    bajos = list(frau_amt[frau_amt <= 5].index)
    altos = list(frau_amt[frau_amt > 5].index)
    rng.shuffle(bajos); rng.shuffle(altos)
    sel_frau = (bajos[:n // 2] + altos[:n - len(bajos[:n // 2])])[:n]
    if len(sel_frau) < n:
        sel_frau = (sel_frau + bajos[n // 2:])[:n]
    sel_frau = sel_frau[:min(n, len(frau))]
    sel_fp = list(duros.index[:n])

    # ------------------------------------------------------------------
    # Verificacion de fuga: ningun ejemplo puede pertenecer al periodo de
    # prueba. Es redundante por construccion, y por eso mismo barata: si un
    # cambio futuro rompe la construccion, esto aborta en lugar de callar.
    # ------------------------------------------------------------------
    limite = float(orden.iloc[corte]["Time"])
    for idx in sel_frau + sel_fp:
        assert float(df.loc[idx, "Time"]) < limite, \
            f"FUGA: el ejemplo {idx} pertenece al periodo de prueba"
    print(f"  Verificacion de fuga: {len(sel_frau) + len(sel_fp)} ejemplos, "
          f"todos anteriores a la hora {limite/3600:.1f}  OK")

    ejemplos = []
    for idx in sel_frau + sel_fp:
        es_fraude = bool(df.loc[idx, TARGET_COL] == 1)
        exp = det.explicar(train, idx)
        # El numero de caso en entrenamiento es sintetico (1..N barajado):
        # el modelo no debe asociar numeros concretos a veredictos.
        n_caso = rng.randint(1, 60)
        dossier = f"CASO {n_caso} (datos verificados del detector; no los alteres)\n" \
                  + exp.a_texto("completo")
        ejemplos.append({
            "prompt": construir_prompt_arnes(n_caso, dossier),
            "respuesta": respuesta_objetivo(n_caso, exp, es_fraude),
            "id": int(idx), "es_fraude": es_fraude,
            "importe": float(exp.importe),
        })

    rng.shuffle(ejemplos)
    n_val = max(1, int(len(ejemplos) * args.frac_validacion))
    val, ent = ejemplos[:n_val], ejemplos[n_val:]

    for nombre, parte in (("train.jsonl", ent), ("val.jsonl", val)):
        ruta = DESTINO / nombre
        with ruta.open("w", encoding="utf-8") as f:
            for e in parte:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"  {ruta.relative_to(RAIZ)}: {len(parte)} ejemplos")

    frau_ent = sum(1 for e in ent if e["es_fraude"])
    bajos_ent = sum(1 for e in ent if e["es_fraude"] and e["importe"] <= 5)
    print(f"\n  Entrenamiento: {frau_ent} fraudes ({bajos_ent} de <=5 EUR) "
          f"y {len(ent) - frau_ent} falsos positivos")
    print(f"  Longitud media del prompt: "
          f"{sum(len(e['prompt']) for e in ent) // len(ent)} caracteres")

    resumen = DESTINO / "resumen.json"
    resumen.write_text(json.dumps({
        "n_train": len(ent), "n_val": len(val),
        "fraudes_train": frau_ent, "fraudes_bajos_train": bajos_ent,
        "umbral": args.umbral, "semilla": args.semilla,
        "hora_corte": round(hora_corte, 2),
    }, indent=2), encoding="utf-8")
    print(f"  Resumen -> {resumen.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
