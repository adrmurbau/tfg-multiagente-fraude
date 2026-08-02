"""
Operacion en continuo: ventanas cortas en lugar de turnos completos.

Un departamento antifraude no espera cuatro horas para revisar lo que ha
pasado: recibe transacciones continuamente. Este guion reproduce ese regimen
acumulando las transacciones de una ventana corta -cinco minutos por
defecto-, analizandolas y emitiendo el informe antes de pasar a la siguiente.

## Que mide, y por que no es lo que parece

La pregunta obvia -¿aguanta el sistema el tiempo real?- tiene una respuesta
aburrida: aguanta con holgura. En un turno real llegan unos 683 movimientos
cada cinco minutos, de los que el detector eleva 0,9 de media. Seis segundos
de computo por cada trescientos: una ocupacion del 2 %.

Lo interesante es la LATENCIA, es decir el tiempo que transcurre entre que
ocurre una transaccion fraudulenta y que aparece en un informe:

    ventana de 4 h    -> espera media de 120 minutos
    ventana de 1 h    -> espera media de  30 minutos
    ventana de 5 min  -> espera media de   2,5 minutos

Casi cincuenta veces menos sin coste de computo apreciable. En fraude con
tarjeta eso importa: el patron dominante en estos datos es una prueba de
importe minimo seguida de un cargo mayor, de modo que alertar antes o despues
decide si el cargo grande llega a producirse.

## El fallo de diseno que destapa

`seleccionar_casos` tenia una rama de respaldo para que el informe no saliera
vacio cuando no hubiera suficientes casos en rojo. En lotes de cuatro horas no
se ejecuta jamas, porque siempre hay decenas. En ventanas de cinco minutos se
disparaba en el 52 % de ellas y elevaba SESENTA casos -la capacidad entera del
equipo- de los cuales cincuenta y nueve eran transacciones legitimas.

Por eso aqui se invoca con `minimo=0`: en operacion continua, un expediente
vacio es la respuesta correcta y la ventana se salta sin gastar una sola
llamada al modelo.

Uso:
    python scripts/run_streaming.py --sin-llm            # solo medida, segundos
    python scripts/run_streaming.py --ventana 5 --max-ventanas 6
    python scripts/run_streaming.py --ventana 10 --modelo qwen2.5-14b-ctx16k
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# CrewAI y las herramientas que dependen de el se importan de forma perezosa,
# dentro del bloque que los usa: el modo --sin-llm mide tasas de llegada,
# latencia y ocupacion sin invocar al modelo, y no debe exigir tener instalada
# toda la pila de agentes para hacerlo.
from src.config import LLM_MODEL, REPORTS_DIR, TARGET_COL  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_turno  # noqa: E402
from src.evaluacion import medir_sistema, veredictos_por_caso  # noqa: E402

# Limites configurados en src/agents/crew.py. Se replican aqui para poder
# detectar sus firmas en los tiempos medidos.
MAX_EXECUTION_TIME = 180   # segundos por agente
TIMEOUT_HTTP = 240         # segundos por peticion al modelo

# Coste por ventana en modo --sin-llm. NO es 5 s por caso, como suponia una
# version anterior de este guion: la medida real sobre seis ventanas dio entre
# 37 y 402 segundos SIN relacion con el numero de casos, porque el coste lo
# domina el arranque del crew y no la carga. Se usa la mediana observada, y el
# resultado se etiqueta como ESTIMADO en todas las salidas para que nadie lo
# confunda con una medicion.
COSTE_ESTIMADO_POR_VENTANA = 300.0


def parsear_args():
    p = argparse.ArgumentParser(description="Operacion en continuo por ventanas")
    p.add_argument("--ventana", type=float, default=5.0,
                   help="Duracion de la ventana en minutos.")
    p.add_argument("--turno-horas", type=float, default=4.0,
                   help="Duracion total del periodo a recorrer.")
    p.add_argument("--desplazamiento", type=float, default=0.0)
    p.add_argument("--umbral", type=float, default=0.80,
                   help="Corte de probabilidad para elevar un caso.")
    p.add_argument("--capacidad", type=int, default=60)
    p.add_argument("--modelo", default=None)
    p.add_argument("--modo", default="interpreta", choices=("interpreta", "revisa"))
    p.add_argument("--max-ventanas", type=int, default=None,
                   help="Corta tras N ventanas CON casos. Util para probar.")
    p.add_argument("--sin-llm", action="store_true",
                   help="No invoca al modelo: mide solo tasas de llegada, "
                        "latencia teorica y ocupacion. Tarda segundos.")
    return p.parse_args()


def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    seg_ventana = args.ventana * 60

    print("=" * 70)
    print("  OPERACION EN CONTINUO")
    print("=" * 70)
    print(f"  Ventana        : {args.ventana:g} min")
    print(f"  Periodo total  : {args.turno_horas:g} h")
    print(f"  Umbral         : {args.umbral}")
    print(f"  Modo           : {'SIN LLM (solo medida)' if args.sin_llm else args.modo}")

    df = cargar_dataset()
    turno = construir_turno(df, horas=args.turno_horas,
                            desplazamiento_h=args.desplazamiento)
    detector = DetectorFraude()
    t_ini = turno["Time"].min()
    turno = turno.copy()
    turno["_ventana"] = ((turno["Time"] - t_ini) // seg_ventana).astype(int)
    n_ventanas = int(turno["_ventana"].max()) + 1

    print(f"  Transacciones  : {len(turno):,} en {n_ventanas} ventanas")
    print(f"  Fraudes reales : {int(turno[TARGET_COL].sum())}\n")

    registro = []
    n_procesadas = 0

    for v in range(n_ventanas):
        lote = turno[turno["_ventana"] == v].drop(columns="_ventana")
        if lote.empty:
            continue

        t0 = time.perf_counter()
        # minimo=0: en continuo, un expediente vacio es la respuesta correcta.
        # Ver el docstring de seleccionar_casos.
        casos = detector.seleccionar_casos(lote, args.capacidad, args.umbral,
                                           minimo=0)
        t_deteccion = time.perf_counter() - t0

        fila = {
            "ventana": v,
            "transacciones": len(lote),
            "fraudes_reales": int(lote[TARGET_COL].sum()),
            "casos_elevados": len(casos),
            "fraude_elevado": int(casos[TARGET_COL].sum()) if len(casos) else 0,
            "seg_deteccion": round(t_deteccion, 3),
            "seg_llm": 0.0,
        }

        if len(casos) == 0:
            fila["estado"] = "sin casos"
            registro.append(fila)
            print(f"  [{v:>3}] {len(lote):>5} transacciones | sin casos "
                  f"| {t_deteccion*1000:>5.0f} ms")
            continue

        if args.sin_llm:
            fila["seg_llm"] = COSTE_ESTIMADO_POR_VENTANA
            fila["estado"] = "ESTIMADO"
        else:
            from src.agents.crew import construir_crew
            from src.agents.tools import (construir_tabla_casos,
                                          inicializar_contexto, mapa_casos)
            # minimo=0 TAMBIEN aqui, no solo en el conteo de arriba. Sin esto
            # el contexto que alimenta al crew se rellena hasta la capacidad y
            # se investigan 60 casos cuando el marcador dice 1.
            inicializar_contexto(lote, detector, capacidad=args.capacidad,
                                 umbral=args.umbral, minimo=0)
            t1 = time.perf_counter()
            resultado = construir_crew(modo=args.modo, modelo=args.modelo,
                                       nucleo=True, iterativo=True).kickoff()
            fila["seg_llm"] = round(time.perf_counter() - t1, 1)
            fila["estado"] = "procesada"

            try:
                salidas = [t.raw for t in resultado.tasks_output]
                salida_inv = "\n\n".join(salidas[:-1]) if len(salidas) > 1 else str(resultado)
            except AttributeError:
                salidas = [str(resultado)]
                salida_inv = str(resultado)

            # Diagnostico de la varianza. Ventanas con carga parecida han
            # costado entre 37 y 402 s, y hay que saber por que antes de
            # escribir nada sobre ocupacion. Dos firmas a distinguir:
            #   - tiempo por tarea cercano a MAX_EXECUTION_TIME -> el agente
            #     agoto su limite y CrewAI corto o reintento
            #   - salidas vacias o muy cortas -> la tarea no produjo nada
            fila["n_tareas"] = len(salidas)
            fila["seg_por_tarea"] = round(fila["seg_llm"] / max(len(salidas), 1), 1)
            fila["long_salidas"] = [len(s) for s in salidas]
            fila["salidas_vacias"] = sum(1 for s in salidas if len(s.strip()) < 50)
            fila["sospecha_timeout"] = bool(
                fila["seg_por_tarea"] > MAX_EXECUTION_TIME * 0.9
                or fila["salidas_vacias"] > 0)

            met = medir_sistema(lote, detector, salida_inv, args.modo,
                                capacidad=args.capacidad, mapa_casos=mapa_casos(),
                                umbral=args.umbral, minimo=0)
            fila["recall_sistema"] = round(met["recall_sistema"], 3)

            destino = REPORTS_DIR / f"streaming_v{v:03d}.md"
            destino.write_text(
                f"# Informe de ventana {v}\n\n"
                f"- Transacciones: {len(lote)}\n- Casos: {len(casos)}\n\n"
                f"{resultado}\n\n---\n\n"
                f"{construir_tabla_casos(veredictos_por_caso(salida_inv))}\n",
                encoding="utf-8")

        # Latencia: desde que ocurre la transaccion hasta que sale el informe.
        # El informe se emite al cerrar la ventana mas lo que cueste procesarla.
        fin_ventana = t_ini + (v + 1) * seg_ventana
        coste = fila["seg_deteccion"] + fila["seg_llm"]
        if fila["fraude_elevado"]:
            fraudes = casos[casos[TARGET_COL] == 1]
            lat = [(fin_ventana + coste - tt) / 60 for tt in fraudes["Time"]]
            fila["latencia_media_min"] = round(sum(lat) / len(lat), 2)
            fila["latencia_max_min"] = round(max(lat), 2)

        registro.append(fila)
        n_procesadas += 1
        print(f"  [{v:>3}] {len(lote):>5} transacciones | {len(casos):>2} casos "
              f"| {fila['fraude_elevado']} fraude | "
              f"{fila['seg_deteccion']*1000:>5.0f} ms + {fila['seg_llm']:>5.1f} s LLM"
              + (f" | latencia {fila.get('latencia_media_min', 0):>5.1f} min"
                 if "latencia_media_min" in fila else "")
              + ("  <-- SOSPECHA DE TIMEOUT" if fila.get("sospecha_timeout") else ""))

        if args.max_ventanas and n_procesadas >= args.max_ventanas:
            print(f"\n  (corte tras {n_procesadas} ventanas con casos)")
            break

    # ------------------------------------------------------------------
    con_casos = [f for f in registro if f["casos_elevados"] > 0]
    vacias = [f for f in registro if f["casos_elevados"] == 0]
    con_lat = [f for f in registro if "latencia_media_min" in f]

    print("\n" + "=" * 70)
    print("  RESULTADOS")
    print("=" * 70 + "\n")
    print(f"  Ventanas recorridas      : {len(registro)}")
    print(f"    con casos              : {len(con_casos)} "
          f"({len(con_casos)/max(len(registro),1):.0%})")
    print(f"    vacias, sin coste      : {len(vacias)} "
          f"({len(vacias)/max(len(registro),1):.0%})")

    coste_total = sum(f["seg_deteccion"] + f["seg_llm"] for f in registro)
    tiempo_real = len(registro) * seg_ventana
    print(f"\n  Computo total            : {coste_total/60:.1f} min")
    print(f"  Tiempo real cubierto     : {tiempo_real/60:.1f} min")
    print(f"  OCUPACION                : {coste_total/max(tiempo_real,1):.1%}")

    desborde = [f for f in registro
                if f["seg_deteccion"] + f["seg_llm"] > seg_ventana]
    print(f"  Ventanas que no dan tiempo: {len(desborde)}"
          + ("  <-- el sistema se retrasaria" if desborde else "  (ninguna)"))

    if con_lat:
        lat = [f["latencia_media_min"] for f in con_lat]
        print(f"\n  LATENCIA hasta la alerta (sobre {len(con_lat)} ventanas con fraude):")
        print(f"    media                  : {sum(lat)/len(lat):.1f} min")
        print(f"    maxima                 : {max(f['latencia_max_min'] for f in con_lat):.1f} min")
        print(f"    con lotes de {args.turno_horas:g} h seria: "
              f"{args.turno_horas*60/2:.0f} min de media")

    # --- Diagnostico de la varianza -----------------------------------
    proc = [f for f in registro if f.get("estado") == "procesada"]
    if proc:
        segs = sorted(f["seg_llm"] for f in proc)
        print(f"\n  DIAGNOSTICO DEL COSTE (limite por agente: {MAX_EXECUTION_TIME} s)\n")
        print(f"  {'vent.':>6}{'casos':>7}{'tareas':>8}{'seg':>8}"
              f"{'seg/tarea':>11}{'vacias':>8}{'sospecha':>10}")
        print("  " + "-"*58)
        for f in proc:
            print(f"  {f['ventana']:>6}{f['casos_elevados']:>7}{f.get('n_tareas',0):>8}"
                  f"{f['seg_llm']:>8.0f}{f.get('seg_por_tarea',0):>11.1f}"
                  f"{f.get('salidas_vacias',0):>8}"
                  f"{('SI' if f.get('sospecha_timeout') else '-'):>10}")
        print("  " + "-"*58)
        print(f"  Mediana {segs[len(segs)//2]:.0f} s | minimo {segs[0]:.0f} s | "
              f"maximo {segs[-1]:.0f} s | dispersion x{segs[-1]/max(segs[0],1):.0f}")
        sosp = sum(1 for f in proc if f.get("sospecha_timeout"))
        if sosp:
            print(f"  {sosp}/{len(proc)} ventanas con firma de tiempo agotado.")
            print("  Si se confirma, el coste NO escala con la carga: es el limite")
            print("  por agente lo que fija el tiempo, y bajarlo reduciria la")
            print("  ocupacion sin perder trabajo util.")

    if args.sin_llm:
        print("\n  AVISO: los tiempos y la ocupacion son ESTIMADOS "
              f"({COSTE_ESTIMADO_POR_VENTANA:.0f} s por ventana con casos),")
        print("  no medidos. Solo la latencia y las tasas de llegada son reales.")

    sello = datetime.now().strftime("%Y%m%d_%H%M")
    destino = REPORTS_DIR / f"streaming_{args.ventana:g}min_{sello}.json"
    destino.write_text(json.dumps({
        "ventana_min": args.ventana,
        "turno_horas": args.turno_horas,
        "umbral": args.umbral,
        "sin_llm": args.sin_llm,
        "coste_estimado": args.sin_llm,
        "max_execution_time": MAX_EXECUTION_TIME,
        "modelo": args.modelo or LLM_MODEL,
        "ocupacion": coste_total / max(tiempo_real, 1),
        "ventanas_totales": len(registro),
        "ventanas_con_casos": len(con_casos),
        "ventanas_desbordadas": len(desborde),
        "latencia_media_min": (sum(f["latencia_media_min"] for f in con_lat)
                               / len(con_lat)) if con_lat else None,
        "registro": registro,
    }, indent=2), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")


if __name__ == "__main__":
    main()
