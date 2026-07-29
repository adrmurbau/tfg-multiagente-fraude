"""
Reauditar informes guardados con la version actual del auditor.

Existe por una razon concreta: el auditor se corrigio DESPUES de ejecutar el
experimento de 120 corridas, y reejecutarlo entero costaria 84 minutos para
arreglar una sola columna. Como los informes que fallaron la auditoria se
guardan en reports/no_fiables/, se pueden reevaluar sin volver a invocar
ningun modelo.

Los informes que ya pasaron la auditoria no se guardan, pero tampoco hace
falta: una correccion que elimina falsos positivos solo puede mover filas de
NO FIABLE a FIABLE, nunca al contrario. Asi que reauditar los fallos basta
para dejar el CSV correcto.

Las columnas de recall y de descartes NO se tocan: salen de la evaluacion
determinista contra las etiquetas, no del auditor de texto.

Uso:
    python scripts/reauditar.py                       # CSV mas reciente
    python scripts/reauditar.py reports/experimento_20260728_1358.csv
"""

import csv
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import REPORTS_DIR  # noqa: E402
from src.detector.data import cargar_dataset  # noqa: E402
from src.detector.predict import DetectorFraude, construir_lote  # noqa: E402
from src.evaluacion import auditar  # noqa: E402

RE_INFORME = re.compile(
    r"## Informe final\n(.*?)\n---\n\n## Salida del Investigador", re.S
)
RE_NOMBRE = re.compile(r"^(?P<modelo>.+?)_(?P<modo>interpreta|revisa)_s(?P<sem>\d+)_r(?P<rep>\d+)\.md$")


def main():
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csvs = sorted(REPORTS_DIR.glob("experimento_*.csv"))
        if not csvs:
            sys.exit("No hay experimento_*.csv en reports/")
        csv_path = csvs[-1]

    fallos_dir = REPORTS_DIR / "no_fiables"
    if not fallos_dir.exists():
        sys.exit("No hay reports/no_fiables/ — nada que reauditar.")

    print(f"  CSV      : {csv_path.name}")
    df = cargar_dataset()
    det = DetectorFraude()
    cache = {}

    def expediente(sem):
        if sem not in cache:
            lote = construir_lote(df, n=500, n_fraudes=5, random_state=int(sem))
            cache[sem] = (list(det.seleccionar_casos(lote).index), list(lote.index))
        return cache[sem]

    # Reauditar cada informe guardado
    veredictos = {}
    for f in sorted(fallos_dir.glob("*.md")):
        m = RE_NOMBRE.match(f.name)
        if not m:
            continue
        cuerpo = RE_INFORME.search(f.read_text(encoding="utf-8"))
        if not cuerpo:
            print(f"  [aviso] no se pudo extraer el informe de {f.name}")
            continue

        ids_exp, ids_lote = expediente(m["sem"])
        aud = auditar(cuerpo.group(1), ids_exp, ids_lote)
        # El nombre de fichero sustituye ':' por '_'; se normaliza igual al comparar
        clave = (m["modelo"], m["modo"], m["sem"], m["rep"])
        veredictos[clave] = aud
        print(f"  {f.name:<46} -> {aud['veredicto']}")

    # Aplicar al CSV
    filas = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    campos = filas[0].keys() if filas else []
    cambios = 0
    for fila in filas:
        clave = (
            fila["modelo"].replace(":", "_").replace("/", "_"),
            fila["modo"], fila["semilla"], fila["repeticion"],
        )
        aud = veredictos.get(clave)
        if aud and fila["fiable"] != str(aud["fiable"]):
            fila["fiable"] = str(aud["fiable"])
            fila["auditoria"] = aud["veredicto"]
            cambios += 1

    if not cambios:
        print("\n  Nada que corregir: el CSV ya refleja la auditoria actual.")
        return

    shutil.copy(csv_path, csv_path.with_suffix(".csv.bak"))
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(campos))
        w.writeheader()
        w.writerows(filas)

    print(f"\n  {cambios} filas corregidas.")
    print(f"  Original preservado en {csv_path.name}.bak")
    print("  Ejecuta ahora: python scripts/analisis.py")


if __name__ == "__main__":
    main()
