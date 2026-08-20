"""
Preparacion del dataset Sparkov: extension exploratoria del capitulo 6.4.

El dataset ULB (data/creditcard.csv) esta anonimizado por PCA: la seccion 5.1
de la memoria mide que las dos unicas variables interpretables, importe y
hora, apenas contribuyen a la deteccion. Esta extension prueba el sistema
sobre un dataset DISTINTO, con variables de negocio genuinas -comercio,
categoria, distancia domicilio-comercio, edad del titular- y un periodo mas
largo que permite una particion temporal con volumen realista.

Origen de los datos: generador Sparkov (github.com/namebrandon/Sparkov_Data_
Generation), el mismo que produjo el dataset "Credit Card Transactions Fraud
Detection Dataset" de Kaggle (kartik2112/fraud-detection). Se genera aqui en
lugar de descargarlo porque el generador no requiere credenciales y permite
fijar exactamente el periodo y el numero de clientes, cosa que el dataset de
Kaggle no permite.

Es un dataset SIMULADO, no transacciones reales. Es la limitacion que hay
que declarar frente al conjunto principal del trabajo, que si lo es.

Reproduccion exacta:
    git clone --depth 1 https://github.com/namebrandon/Sparkov_Data_Generation
    cd Sparkov_Data_Generation
    pip install Faker==13.12.0 numpy
    python datagen.py -n 1000 -o gen_1y 01-01-2024 12-31-2024 -seed 42

Uso de este script:
    python scripts/sparkov/preparar_dataset.py --entrada <carpeta_gen_1y>
"""

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
SALIDA = ROOT / "data" / "sparkov"

# Ultimos dos meses del periodo a prueba: deja diez meses de entrenamiento y
# una ventana de prueba con volumen suficiente, a diferencia de las pocas
# horas que deja la particion temporal del dataset ULB.
CORTE_TEST = "2024-11-01"


def radianes(grados):
    return grados * np.pi / 180


def distancia_km(lat1, lon1, lat2, lon2):
    """Distancia entre domicilio y comercio, formula de haversine."""
    R = 6371.0
    dlat = radianes(lat2 - lat1)
    dlon = radianes(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(radianes(lat1)) * np.cos(radianes(lat2)) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(a))


def cargar_crudo(carpeta: Path) -> pd.DataFrame:
    """Fusiona los ficheros por perfil que produce el generador.

    El generador reparte las transacciones en un fichero por perfil demografico
    y fragmento de clientes, y deja ficheros casi vacios (solo cabecera de
    cliente, sin columnas de transaccion) cuando ningun cliente del fragmento
    encaja en el perfil. Se descartan por esa cabecera corta.
    """
    marcos = []
    for f in glob.glob(str(carpeta / "*.csv")):
        with open(f, encoding="utf-8", errors="ignore") as fh:
            cabecera = fh.readline()
        if "trans_num" not in cabecera:
            continue
        df = pd.read_csv(f, sep="|")
        if len(df):
            marcos.append(df)
    if not marcos:
        raise FileNotFoundError(f"No se encontraron ficheros de transacciones en {carpeta}")
    return pd.concat(marcos, ignore_index=True)


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Ingenieria de variables de negocio, analoga en espiritu a 4.2.2."""
    df = df.copy()

    # El merchant llega con el prefijo literal "fraud_" en TODAS las filas,
    # fraudulentas o no: es un artefacto de nomenclatura del generador, no una
    # fuga de la etiqueta (se comprobo que no coincide con is_fraud). Se retira
    # por legibilidad.
    df["comercio"] = df["merchant"].str.replace("^fraud_", "", regex=True)

    marca = pd.to_datetime(df["trans_date"] + " " + df["trans_time"])
    df["marca_temporal"] = marca
    df["hora"] = marca.dt.hour + marca.dt.minute / 60
    df["dia_semana"] = marca.dt.dayofweek

    nacimiento = pd.to_datetime(df["dob"])
    df["edad"] = (marca - nacimiento).dt.days / 365.25

    df["distancia_km"] = distancia_km(df["lat"], df["long"], df["merch_lat"], df["merch_long"])

    df["importe"] = df["amt"]
    df["poblacion_ciudad"] = df["city_pop"]
    df["categoria"] = df["category"]
    df["es_fraude"] = df["is_fraud"]

    cols = ["marca_temporal", "trans_num", "cc_num", "comercio", "categoria",
            "importe", "hora", "dia_semana", "edad", "distancia_km",
            "poblacion_ciudad", "city", "state", "job", "es_fraude"]
    return df[cols].sort_values("marca_temporal").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", required=True, help="carpeta con los CSV crudos del generador")
    args = ap.parse_args()

    print("=" * 66)
    print("  PREPARACION DEL DATASET SPARKOV")
    print("=" * 66)

    crudo = cargar_crudo(Path(args.entrada))
    print(f"\n  Filas crudas: {len(crudo):,}")

    df = preparar(crudo)
    print(f"  Filas preparadas: {len(df):,}")
    print(f"  Fraude: {int(df['es_fraude'].sum()):,} ({df['es_fraude'].mean() * 100:.3f}%)")
    print(f"  Periodo: {df['marca_temporal'].min()} -> {df['marca_temporal'].max()}")
    print(f"  Clientes: {df['cc_num'].nunique():,}  Comercios: {df['comercio'].nunique():,}"
          f"  Categorias: {df['categoria'].nunique()}")

    corte = pd.Timestamp(CORTE_TEST)
    train = df[df["marca_temporal"] < corte]
    test = df[df["marca_temporal"] >= corte]
    print(f"\n  Particion temporal, corte en {CORTE_TEST}:")
    print(f"    train: {len(train):,} ({int(train['es_fraude'].sum())} fraudes, "
          f"{train['es_fraude'].mean() * 100:.3f}%)")
    print(f"    test : {len(test):,} ({int(test['es_fraude'].sum())} fraudes, "
          f"{test['es_fraude'].mean() * 100:.3f}%)")

    SALIDA.mkdir(parents=True, exist_ok=True)
    train.to_csv(SALIDA / "train.csv", index=False)
    test.to_csv(SALIDA / "test.csv", index=False)
    print(f"\n  Guardado en {SALIDA}")


if __name__ == "__main__":
    main()
