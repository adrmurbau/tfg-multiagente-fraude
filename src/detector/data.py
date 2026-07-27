"""
Carga y particionado del dataset ULB.

Se implementan DOS estrategias de split a proposito, porque miden cosas
distintas y la comparacion es en si misma un resultado del trabajo:

  - aleatorio estratificado: el estandar en la literatura sobre este dataset,
    permite comparar metricas con los papers publicados. Pero mezcla pasado y
    futuro, asi que sobreestima el rendimiento real.

  - temporal: entrena con las primeras transacciones y valida con las ultimas,
    que es lo unico que puede hacer un sistema en produccion. Metricas mas
    bajas pero honestas.
"""

import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import (
    DATASET_CSV,
    FEATURE_COLS,
    RANDOM_STATE,
    TARGET_COL,
    TEST_SIZE,
    TIME_COL,
)


def cargar_dataset(ruta=None) -> pd.DataFrame:
    """Carga el CSV y anade la unica variable derivada: la hora del dia."""
    ruta = ruta or DATASET_CSV
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encuentra {ruta}. Descarga el dataset ULB de Kaggle "
            "y dejalo en data/creditcard.csv"
        )

    df = pd.read_csv(ruta)

    # Time = segundos desde la primera transaccion del periodo (2 dias).
    # La hora del dia si generaliza; el segundo absoluto no.
    df["Hour"] = (df[TIME_COL] / 3600) % 24

    return df


def split_aleatorio(df: pd.DataFrame):
    """Particion aleatoria estratificada por clase."""
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    return train_test_split(
        X, y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
    )


def split_temporal(df: pd.DataFrame):
    """Particion cronologica: primeras transacciones a train, ultimas a test."""
    df = df.sort_values(TIME_COL).reset_index(drop=True)
    corte = int(len(df) * (1 - TEST_SIZE))

    train, test = df.iloc[:corte], df.iloc[corte:]

    return (
        train[FEATURE_COLS], test[FEATURE_COLS],
        train[TARGET_COL], test[TARGET_COL],
    )


SPLITS = {
    "aleatorio": split_aleatorio,
    "temporal": split_temporal,
}


def resumen_split(nombre, y_train, y_test) -> str:
    return (
        f"  split '{nombre}': "
        f"train {len(y_train):,} ({int(y_train.sum())} fraudes, "
        f"{y_train.mean() * 100:.3f}%) | "
        f"test {len(y_test):,} ({int(y_test.sum())} fraudes, "
        f"{y_test.mean() * 100:.3f}%)"
    )
