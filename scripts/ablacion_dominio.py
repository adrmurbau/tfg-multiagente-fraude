"""
Ablacion de la correccion de dominio: ¿cambia el veredicto o solo la prosa?

## De donde sale este experimento

Al cerrar el objetivo 4 se observo que Qwen2.5-72B descartaba los dos unicos
fraudes de la cola alegando de forma explicita que el importe era reducido
-1,00 y 2,22 EUR-. En estos datos esa premisa esta invertida: el importe
mediano de un fraude es 2,11 EUR frente a 19,99 de una legitima, y el 59,3 %
de los fraudes no llega a 5 EUR frente al 25,1 % de las legitimas.

Parecia, pues, un fallo barato de corregir: bastaba con retirar la premisa
falsa del prompt. La constante DOMINIO de src/agents/prompts.py hace eso, y
con cuidado de no instalar la contraria -decir "importe bajo indica fraude"
entregaria la respuesta en la entrada y repetiria el defecto de diseno que ya
obligo a rehacer el experimento del dossier-.

Una primera ejecucion con qwen2.5:14b sobre los casos 44-55 dio:

    sin correccion : 12 descartes, 2 fraudes destruidos, 10 aciertos
    con correccion : 11 descartes y 1 confirmacion, 2 destruidos, 9 aciertos

No salvo ninguno de los dos fraudes, y la unica confirmacion fue un caso
legitimo. Pero el texto SI cambio, y de forma llamativa. Sobre el caso 50 el
modelo escribio que "podria ser un intento inicial de verificacion antes de
una transaccion mas grande" y a continuacion emitio DESCARTADO. Sobre el 55,
"pese al bajo importe habitualmente asociado a intentos preliminares de uso
fraudulento", y DESCARTADO. Sobre el 53, "puede ser una tactica comun en
intentos de fraude para probar la tarjeta", y DESCARTADO.

## Que mide este guion

La hipotesis que se deriva de lo anterior es que la explicacion no es la razon
de la decision: se genera aparte. Si fuese la razon, un texto que reconoce el
patron de fraude deberia acompanarse de una confirmacion.

Se mide por tanto, ademas de lo habitual, la TASA DE CONTRADICCION: casos en
los que la prosa menciona el patron del cargo de prueba y el veredicto es
DESCARTADO. Es la cifra que convierte una observacion cualitativa -visible en
tres salidas- en un resultado con denominador.

Conviene ser claro sobre su alcance. Una tasa alta demuestra que prosa y
veredicto no van juntos; NO demuestra por que mecanismo interno ocurre eso, y
no debe redactarse como si lo hiciera.

## Diseno

Cada replica es un TURNO DISTINTO, obtenido desplazando el inicio, no una
semilla de muestreo. Con temperature=0.1 repetir el mismo turno daria casi la
misma salida y el n seria ficticio. Al mover el turno cambian las
transacciones, el expediente y los fraudes que caen en la cola.

Uso:
    python scripts/ablacion_dominio.py --solo-estimar
    python scripts/ablacion_dominio.py
    python scripts/ablacion_dominio.py --modelos qwen2.5-14b-ctx16k --turnos 0 4 8
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import REPORTS_DIR, TARGET_COL  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_turno  # noqa: E402
from src.evaluacion import veredictos_por_caso  # noqa: E402

# gpt-oss-20b queda fuera por defecto: es un modelo de razonamiento y con el
# presupuesto de tokens de este arnes agota la cuota pensando, devolviendo una
# respuesta vacia y cero veredictos. Puede incluirse a mano subiendo
# --max-tokens, pero entonces su coste por caso deja de ser comparable.
MODELOS = ["llama3.1-8b-ctx16k", "qwen2.5-14b-ctx16k"]
# Desplazamientos del inicio del turno, en horas. El periodo de test dura
# 7,7 h -de la hora 40,3 a la 48,0-, de modo que con turnos de 4 h el
# desplazamiento no puede pasar de 3,7. Una primera version uso 0, 4, 8, 12,
# 16 y 20 sin comprobarlo y la ejecucion aborto a mitad. experimento.py usa
# 0, 1, 2 y 3 por esta misma razon.
TURNOS = [0.0, 1.0, 2.0, 3.0]

# Coste por caso medido con el arnes, en segundos. Solo para estimar antes de
# lanzar; los tiempos reales se registran en el fichero de resultados.
SEG_POR_CASO = {"llama3.1-8b-ctx16k": 2.5,
                "qwen2.5-14b-ctx16k": 4.3,
                "gpt-oss-20b-ctx16k": 9.0}
SEG_POR_CASO_DESCONOCIDO = 5.0

# Reconocimiento del patron en la prosa. Se exige la coincidencia de DOS
# familias -la idea de prueba o tanteo, y la de un cargo posterior mayor-
# porque cualquiera de ellas por separado aparece en contextos inocuos: el
# modelo habla de "importe bajo" continuamente sin aludir al patron.
_RE_PRUEBA = re.compile(
    r"\b(prueba|probar|tante|verificaci[oó]n|verificar|comprobar|"
    r"preliminar(es)?|inicial(es)?|test(eo|ear)?)\b", re.IGNORECASE)
_RE_POSTERIOR = re.compile(
    r"(cargo|transacci[oó]n|compra|importe)s?\s+(m[aá]s\s+)?"
    r"(grande|mayor|elevad|alt)|"
    r"antes\s+de\s+(realizar|efectuar|un|una)|"
    r"posterior(es|mente)?|"
    r"despu[eé]s\s+(de|realic|har)", re.IGNORECASE)


def menciona_patron(texto: str) -> bool:
    """¿La prosa alude al patron del cargo de prueba previo al cargo grande?

    Deliberadamente conservador: prefiere no contar una mencion dudosa a
    inflar la tasa de contradiccion, que es la cifra que sostiene la
    conclusion. Los falsos negativos la subestiman, que es el lado seguro.
    """
    # Se recorta en el veredicto: lo que el modelo escriba despues no forma
    # parte del razonamiento que precede a la decision.
    m = re.search(r"(?:VEREDICTO|VERDICT):", texto, re.IGNORECASE)
    cuerpo = texto[:m.start()] if m else texto
    return bool(_RE_PRUEBA.search(cuerpo) and _RE_POSTERIOR.search(cuerpo))


def parsear_args():
    p = argparse.ArgumentParser(description="Ablacion de la correccion de dominio")
    p.add_argument("--modelos", nargs="+", default=MODELOS)
    p.add_argument("--turnos", nargs="+", type=float, default=TURNOS,
                   help="Desplazamientos en horas del inicio del turno. Cada "
                        "uno es una replica independiente.")
    p.add_argument("--max-casos", type=int, default=12)
    p.add_argument("--umbral", type=float, default=0.05)
    p.add_argument("--max-tokens", type=int, default=220,
                   help="Tokens de respuesta por caso. Los modelos de "
                        "razonamiento necesitan bastantes mas: gpt-oss-20b "
                        "agota 220 pensando y devuelve una respuesta vacia, "
                        "pero con 800 responde con normalidad. Al cambiarlo, "
                        "el coste por caso deja de ser comparable con el de "
                        "las demas ejecuciones.")
    p.add_argument("--solo-estimar", action="store_true",
                   help="Calcula cuanto tardaria y no ejecuta nada.")
    return p.parse_args()


def ejecutar(modelo, turno, dominio, args):
    """Invoca el arnes como proceso aparte y devuelve su fichero de resultados.

    Se lanza como subproceso, y no importando main(), para que cada ejecucion
    parta de un contexto limpio: el expediente vive en un objeto de modulo y
    reutilizarlo entre turnos distintos es justo el tipo de fuga que este
    trabajo lleva ya dos veces encontrando.
    """
    cmd = [sys.executable, "scripts/investigador_solo.py",
           "--backend", "ollama", "--modelo", modelo,
           "--max-casos", str(args.max_casos), "--umbral", str(args.umbral),
           "--desplazamiento", str(turno),
           "--max-tokens", str(args.max_tokens)]
    if dominio:
        cmd.append("--dominio")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 2:
        print(f"    [OMITIDO] turno +{turno:g}h fuera del periodo de test")
        return None
    # Se lee la ruta que el propio arnes declara. Localizarla comparando el
    # contenido del directorio antes y despues fallaba: el nombre se derivaba
    # de la hora con resolucion de minuto y dos ejecuciones de medio minuto
    # caian en el mismo nombre, de modo que la segunda sobrescribia a la
    # primera y la diferencia de conjuntos salia vacia. Se registraba entonces
    # un error inexistente sobre una ejecucion que habia terminado bien.
    m = re.search(r"Resultados -> (.+\.json)", r.stdout)
    if not m:
        print(f"    [ERROR] el arnes no declaro fichero de resultados "
              f"(codigo {r.returncode}). Ultimas lineas:")
        for linea in r.stdout.strip().splitlines()[-4:]:
            print(f"       {linea}")
        return None
    return json.loads(Path(m.group(1).strip()).read_text(encoding="utf-8"))


def main():
    args = parsear_args()
    REPORTS_DIR.mkdir(exist_ok=True)

    n_ejec = len(args.modelos) * len(args.turnos) * 2
    seg = sum(SEG_POR_CASO.get(m, SEG_POR_CASO_DESCONOCIDO) * args.max_casos
              for m in args.modelos) * len(args.turnos) * 2

    print("=" * 70)
    print("  ABLACION DE LA CORRECCION DE DOMINIO")
    print("=" * 70)
    print(f"  Modelos   : {', '.join(args.modelos)}")
    print(f"  Turnos    : {', '.join(f'{t:g}h' for t in args.turnos)}")
    print(f"  Ejecuciones: {n_ejec} ({len(args.turnos)} turnos x "
          f"{len(args.modelos)} modelos x 2 condiciones)")
    print(f"  Tokens por caso: {args.max_tokens}"
          + ("  [no comparable con las tandas de 220]"
             if args.max_tokens != 220 else ""))
    print(f"  Duracion ESTIMADA: {seg/60:.0f} min\n")
    if args.solo_estimar:
        return

    filas, excluidas, t0 = [], [], time.perf_counter()
    for turno in args.turnos:
        # El detector y el turno se reconstruyen aqui solo para saber que
        # casos del expediente son fraude; el arnes lo hace por su cuenta.
        df = cargar_dataset()
        lote = construir_turno(df, horas=4.0, desplazamiento_h=turno)
        det = DetectorFraude()
        print(f"  turno +{turno:g}h  ({len(lote):,} transacciones, "
              f"{int(lote[TARGET_COL].sum())} fraudes)")

        for modelo in args.modelos:
            for dominio in (False, True):
                a = ejecutar(modelo, turno, dominio, args)
                if a is None:
                    continue
                casos, salidas = a["casos"], a["salidas"]
                ver = {int(k): v for k, v in a["veredictos"].items()}
                # Se exige extraccion COMPLETA. Una version anterior solo
                # descartaba la ejecucion cuando no habia ningun veredicto, de
                # modo que una con siete de doce se agregaba en silencio y
                # aparecia en la tabla resumen indistinguible de una integra.
                # Con gpt-oss-20b, que agota el presupuesto de tokens
                # razonando y corta la respuesta a mitad de frase, eso producia
                # recuentos calculados sobre una fraccion de los casos y
                # presentados como si fueran comparables con los demas.
                #
                # Es el mismo modo de fallo que este trabajo documenta en otros
                # sitios: nada falla, y el resultado tiene aspecto de dato.
                if len(ver) < len(casos):
                    vacias = sum(1 for s in salidas if not s.strip())
                    print(f"    [EXCLUIDA] {modelo} dominio="
                          f"{'SI' if dominio else 'no'}: "
                          f"{len(ver)}/{len(casos)} veredictos"
                          + (f", {vacias} salidas vacias" if vacias else "")
                          + ". Extraccion incompleta.")
                    excluidas.append({"modelo": modelo, "turno": turno,
                                      "dominio": dominio,
                                      "veredictos": len(ver),
                                      "casos": len(casos), "vacias": vacias})
                    continue

                menciones = contradic = 0
                for n, s in zip(casos, salidas):
                    if menciona_patron(s):
                        menciones += 1
                        if ver.get(n) == "DESCARTADO":
                            contradic += 1

                filas.append({
                    "modelo": modelo, "turno": turno, "dominio": dominio,
                    "casos": len(casos),
                    "confirmados": sum(1 for v in ver.values() if v == "CONFIRMADO"),
                    "descartados": sum(1 for v in ver.values() if v == "DESCARTADO"),
                    "fraude_destruido": a["fraude_destruido"],
                    "descartes_correctos": a["descartes_correctos"],
                    "menciona_patron": menciones,
                    "contradicciones": contradic,
                })
                f = filas[-1]
                print(f"    {modelo:<22} dominio={'SI' if dominio else 'no':<3} "
                      f"| conf {f['confirmados']:>2} desc {f['descartados']:>2} "
                      f"| destruido {f['fraude_destruido']} "
                      f"| patron {menciones:>2}, contradice {contradic:>2}")

    if excluidas:
        print(f"\n  [ATENCION] {len(excluidas)} de "
              f"{len(excluidas) + len(filas)} ejecuciones excluidas por "
              f"extraccion incompleta de veredictos.")
        porm = {}
        for e in excluidas:
            porm[e["modelo"]] = porm.get(e["modelo"], 0) + 1
        for m, c in porm.items():
            print(f"      {m}: {c}")
        print("  Sus cifras NO estan en la tabla de abajo. Un modelo con")
        print("  exclusiones no es comparable con uno sin ellas.")

    if not filas:
        print("\n  Sin resultados utilizables.")
        return

    print("\n" + "=" * 70)
    print("  RESUMEN POR CONDICION")
    print("=" * 70 + "\n")
    print(f"  {'modelo':<22}{'dominio':>8}{'destr.':>8}{'conf.':>7}"
          f"{'patron':>8}{'contra':>8}{'tasa':>8}")
    print("  " + "-" * 69)
    for modelo in args.modelos:
        for dominio in (False, True):
            g = [f for f in filas if f["modelo"] == modelo and f["dominio"] == dominio]
            if not g:
                continue
            m = sum(f["menciona_patron"] for f in g)
            c = sum(f["contradicciones"] for f in g)
            print(f"  {modelo:<22}{'SI' if dominio else 'no':>8}"
                  f"{sum(f['fraude_destruido'] for f in g):>8}"
                  f"{sum(f['confirmados'] for f in g):>7}"
                  f"{m:>8}{c:>8}"
                  f"{(f'{100*c/m:.0f}%' if m else '-'):>8}")

    print("\n  Lectura:")
    tot_m = sum(f["menciona_patron"] for f in filas if f["dominio"])
    tot_c = sum(f["contradicciones"] for f in filas if f["dominio"])
    d_sin = sum(f["fraude_destruido"] for f in filas if not f["dominio"])
    d_con = sum(f["fraude_destruido"] for f in filas if f["dominio"])
    print(f"    Fraude destruido: {d_sin} sin la correccion, {d_con} con ella.")
    if tot_m:
        print(f"    Con la correccion, la prosa menciona el patron del cargo de")
        print(f"    prueba en {tot_m} casos y en {tot_c} de ellos ({100*tot_c/tot_m:.0f} %)")
        print(f"    el veredicto es DESCARTADO pese a haberlo reconocido.")
        if tot_c / tot_m > 0.8:
            print("\n    La prosa y el veredicto no van juntos. El texto absorbe la")
            print("    correccion y la decision no se mueve, lo que indica que la")
            print("    explicacion no es la razon de la decision sino una")
            print("    racionalizacion posterior. No se afirma nada sobre el")
            print("    mecanismo interno que produce esa disociacion.")
    else:
        print("    La prosa no menciona el patron en ningun caso: la correccion")
        print("    no llego a incorporarse al texto y el experimento no dice")
        print("    nada sobre la relacion entre prosa y veredicto.")

    marca = datetime.now().strftime("%Y%m%d_%H%M")
    destino = REPORTS_DIR / f"ablacion_dominio_{marca}.json"
    destino.write_text(json.dumps({
        "generado": marca, "modelos": args.modelos, "turnos": args.turnos,
        "max_casos": args.max_casos, "umbral": args.umbral,
        "max_tokens": args.max_tokens,
        "minutos_reales": round((time.perf_counter() - t0) / 60, 1),
        "filas": filas, "excluidas": excluidas,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Resultados -> {destino}")


if __name__ == "__main__":
    main()
