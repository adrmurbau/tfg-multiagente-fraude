"""
Cola del expediente Sparkov, en dos versiones del mismo caso: extension de 5.13.

La comparacion de 5.13 (ULB anonimizado vs Sparkov de negocio) tiene un problema
de fondo: son dos datasets distintos, y cualquier diferencia de comportamiento
del modelo podria deberse al dominio, al detector, al nivel de fraude o a la
legibilidad de las variables, todo a la vez. Este guion aisla ESA UNICA
variable. Para los mismos casos, con el mismo detector y las mismas
contribuciones numericas, genera dos dossiers:

    completo   comercio, categoria, edad, distancia, poblacion -> nombres reales
    reducido   las mismas variables de negocio se anonimizan como "var_N", en
               el mismo orden de aporte. Solo importe y hora, las dos variables
               interpretables que tambien tiene el dataset ULB, conservan su
               nombre. Es la reconstruccion mas fiel posible del techo de
               legibilidad de 4.2.1 sobre datos que en realidad SI son de
               negocio.

Si el modelo razona distinto entre ambas versiones del MISMO caso, la
diferencia es atribuible a la legibilidad y no al dataset.

Seleccion de casos: el detector NO esta calibrado (5.13 lo entrena sin
busqueda de hiperparametros) y la mediana de probabilidad sobre el conjunto de
prueba completo es 0,95 -la mayoria de las transacciones, fraude o no, reciben
probabilidad alta-, de modo que un "expediente" definido por posicion en el
ranking no aisla casos dudosos: todos rondan 1,0000. Se seleccionan en su
lugar los casos donde el desacuerdo entre el detector y la realidad es mayor:

    cola de fraude   fraude real con la probabilidad MAS BAJA de todo el
                      conjunto de prueba -el detector apenas los nota-.
    controles         transacciones legitimas con la probabilidad MAS ALTA
                      -el detector las senala con mas confianza, sin razon-.

Uso:
    python scripts/sparkov/generar_cola.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parent.parent.parent
DATOS = ROOT / "data" / "sparkov"
REPORTES = ROOT / "reports"

NUMERICAS = ["importe", "hora", "dia_semana", "edad", "distancia_km", "poblacion_ciudad"]
CATEGORICA = "categoria"
OBJETIVO = "es_fraude"

N_COLA_FRAUDE = 6
N_CONTROLES = 3

# Variables que se anonimizan en la version "reducida": todo lo que un dataset
# anonimizado tipo ULB no podria mostrar. Importe y hora se conservan porque
# son las dos unicas variables interpretables que ULB tambien tiene con
# nombre (4.2.1); dia_semana se anonimiza junto al resto porque ULB, con solo
# 48 horas de periodo, no tiene un equivalente informativo.
VARIABLES_DE_NEGOCIO = {"edad", "distancia_km", "poblacion_ciudad", "dia_semana"}


def construir_variables(train, test):
    cod = OneHotEncoder(sparse_output=False, handle_unknown="ignore", dtype=np.float32)
    cod.fit(train[[CATEGORICA]])
    nombres_cat = [f"categoria_{c}" for c in cod.categories_[0]]

    def transformar(df):
        cat = pd.DataFrame(cod.transform(df[[CATEGORICA]]), columns=nombres_cat,
                            index=df.index).reset_index(drop=True)
        num = df[NUMERICAS].reset_index(drop=True)
        return pd.concat([num, cat], axis=1)

    return transformar(train), transformar(test), NUMERICAS + nombres_cat


def es_de_negocio(nombre_variable: str) -> bool:
    return nombre_variable in VARIABLES_DE_NEGOCIO or nombre_variable.startswith("categoria_")


def contribuciones(booster, fila_X, columnas):
    dm = xgb.DMatrix(fila_X.to_frame().T, feature_names=columnas)
    contrib = booster.predict(dm, pred_contribs=True)[0]
    pares = list(zip(columnas + ["sesgo_base"], contrib))
    pares.sort(key=lambda p: -abs(p[1]))
    return pares


def dossier_completo(fila, prob, contrib, n, top=6):
    lineas = "\n".join(f"  {var}: {val:+.3f}" for var, val in contrib[:top])
    return (
        f"CASO {n}\n"
        f"Comercio: {fila['comercio']}\n"
        f"Categoria de comercio: {fila['categoria']}\n"
        f"Importe: {fila['importe']:.2f} USD\n"
        f"Hora del dia: {fila['hora']:.1f} h\n"
        f"Edad del titular: {fila['edad']:.0f} anios\n"
        f"Distancia domicilio-comercio: {fila['distancia_km']:.1f} km\n"
        f"Poblacion de la ciudad del titular: {int(fila['poblacion_ciudad']):,}\n"
        f"Probabilidad de fraude segun el detector: {prob:.4f}\n"
        f"Contribuciones principales del detector (Shapley, XGBoost):\n{lineas}"
    )


def dossier_reducido(fila, prob, contrib, n, top=6):
    """Igual informacion numerica, variables de negocio anonimizadas.

    No se omiten: se RENOMBRAN, para que el numero de senales visibles sea
    identico al de la version completa y la unica diferencia sea si el
    nombre dice algo reconocible.
    """
    contador = 0
    lineas = []
    for var, val in contrib[:top]:
        if es_de_negocio(var):
            contador += 1
            etiqueta = f"var_{contador}"
        else:
            etiqueta = var
        lineas.append(f"  {etiqueta}: {val:+.3f}")
    return (
        f"CASO {n}\n"
        f"Importe: {fila['importe']:.2f} USD\n"
        f"Hora del dia: {fila['hora']:.1f} h\n"
        f"Probabilidad de fraude segun el detector: {prob:.4f}\n"
        f"Contribuciones principales del detector (Shapley, XGBoost), variables "
        f"sin identificar salvo importe y hora:\n" + "\n".join(lineas)
    )


def main():
    print("=" * 66)
    print("  COLA DEL EXPEDIENTE SPARKOV: COMPLETO VS REDUCIDO")
    print("=" * 66)

    train = pd.read_csv(DATOS / "train.csv")
    test = pd.read_csv(DATOS / "test.csv").reset_index(drop=True)
    X_train, X_test, columnas = construir_variables(train, test)
    assert X_test.shape[1] == len(columnas), (X_test.shape, len(columnas))
    assert len(X_test) == len(test)

    modelo = xgb.XGBClassifier()
    modelo.load_model(ROOT / "models" / "xgboost_sparkov.json")
    booster = modelo.get_booster()

    score = modelo.predict_proba(X_test)[:, 1]
    test["probabilidad"] = score
    print(f"\n  Mediana de probabilidad sobre el conjunto de prueba: {np.median(score):.4f}")

    cola_fraude = test[test[OBJETIVO] == 1].nsmallest(N_COLA_FRAUDE, "probabilidad")
    controles = test[test[OBJETIVO] == 0].nlargest(N_CONTROLES, "probabilidad")
    seleccion = pd.concat([cola_fraude, controles]).sort_values("probabilidad")

    print(f"  Cola de fraude (probabilidad mas baja entre fraude real): "
          f"{len(cola_fraude)} casos, rango "
          f"{cola_fraude['probabilidad'].min():.4f}-{cola_fraude['probabilidad'].max():.4f}")
    print(f"  Controles (probabilidad mas alta entre legitimas): "
          f"{len(controles)} casos, rango "
          f"{controles['probabilidad'].min():.4f}-{controles['probabilidad'].max():.4f}")

    casos = []
    for i, (pos, fila) in enumerate(seleccion.iterrows(), start=1):
        contrib = contribuciones(booster, X_test.loc[pos], columnas)
        completo = dossier_completo(fila, fila["probabilidad"], contrib, i)
        reducido = dossier_reducido(fila, fila["probabilidad"], contrib, i)
        casos.append({
            "n": i, "comercio": fila["comercio"], "categoria": fila["categoria"],
            "importe": float(fila["importe"]), "probabilidad": float(fila["probabilidad"]),
            "es_fraude": bool(fila[OBJETIVO]),
            "dossier_completo": completo, "dossier_reducido": reducido,
        })
        print(f"\n  [{i}] {'FRAUDE' if fila[OBJETIVO] else 'legitima':<9} "
              f"p={fila['probabilidad']:.4f}  {fila['comercio']} | {fila['categoria']} | "
              f"{fila['importe']:.2f} USD")

    REPORTES.mkdir(exist_ok=True)
    destino = REPORTES / "sparkov_cola.json"
    destino.write_text(json.dumps({"casos": casos}, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\n  Guardado -> {destino}")
    print("  Siguiente paso: python scripts\\sparkov\\investigar_cola.py --modelo <modelo>")


if __name__ == "__main__":
    main()
