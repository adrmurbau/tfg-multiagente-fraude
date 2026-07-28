"""
Pruebas de regresion del auditor - SIN LLM.

Cada caso de este fichero corresponde a un fallo REAL detectado durante el
desarrollo. El auditor ha dado cuatro falsos positivos y ha dejado pasar una
alucinacion completa; sin estas pruebas, cada correccion arriesgaba reabrir
un fallo anterior.

Un auditor que grita cuando no debe acaba ignorandose, y entonces deja de
proteger de nada. Por eso los falsos positivos se prueban igual que los
verdaderos.

Uso:
    python scripts/test_auditor.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluacion import auditar, ids_citados, veredictos_por_caso  # noqa: E402

EXPEDIENTE = [34, 156, 352, 420]
LOTE = list(range(500))

# ----------------------------------------------------------------------
# Casos: (nombre, texto, debe_ser_fiable, motivo historico)
# ----------------------------------------------------------------------
CASOS = [
    (
        "Informe fabricado (fallo original)",
        """**Tabla de Casos Priorizados**
| 0 | $500 | V14 | ALTO (Rojo) |
| 1 | $200 | V21 | ALTO (Rojo) |
#### Transacción 0
Tarjeta utilizada en una transaccion sospechosa en un pais de alto riesgo.
#### Transacción 1
Cuenta con historial de cliente sospechoso.""",
        False,
        "cinco transacciones inventadas con importes en dolares",
    ),
    (
        "Locucion 'tener en cuenta' (llama)",
        """| 156 | 1.0000 | ALTO | 1.18 EUR |
| 34 | 1.0000 | ALTO | 0.76 EUR |
| 420 | 0.9989 | ALTO | 39.98 EUR |
| 352 | 0.9736 | ALTO | 0.76 EUR |
Es importante tener en cuenta que la precision depende del modelo utilizado.""",
        True,
        "'cuenta' suelta disparaba la alarma sobre un informe correcto",
    ),
    (
        "Porcentaje '100%' (qwen2.5)",
        """| 156 | 1.0000 | ALTO | 1.18 EUR |
| 34 | 1.0000 | ALTO | 0.76 EUR |
| 420 | 0.9989 | ALTO | 39.98 EUR |
| 352 | 0.9736 | ALTO | 0.76 EUR |
Probabilidad de fraude del 100% o muy cercana a ella.""",
        True,
        "'100%' se leia como la transaccion numero 100",
    ),
    (
        "Declaracion de cumplimiento (qwen3)",
        """| 156 | 1.0000 | ALTO | 1.18 EUR |
| 34 | 1.0000 | ALTO | 0.76 EUR |
| 420 | 0.9989 | ALTO | 39.98 EUR |
| 352 | 0.9736 | ALTO | 0.76 EUR |
Se han identificado 4 casos de alto riesgo.
Las explicaciones se basan exclusivamente en el analisis del investigador,
sin mencionar paises, comercios, cuentas, titulares ni historial de cliente.""",
        True,
        "citar los terminos vetados DENTRO de una negacion no es inventarselos",
    ),
    (
        "Invencion de frecuencia",
        """| 156 | 1.0000 | ALTO | 1.18 EUR |
| 34 | 1.0000 | ALTO | 0.76 EUR |
| 420 | 0.9989 | ALTO | 39.98 EUR |
| 352 | 0.9736 | ALTO | 0.76 EUR |
La tarjeta se uso varias veces en un corto periodo de tiempo.""",
        False,
        "el dataset no relaciona transacciones entre si",
    ),
    (
        "Invencion geografica afirmativa",
        """| 156 | 1.0000 | ALTO | 1.18 EUR |
| 34 | 1.0000 | ALTO | 0.76 EUR |
| 420 | 0.9989 | ALTO | 39.98 EUR |
| 352 | 0.9736 | ALTO | 0.76 EUR |
La operacion se realizo en un pais de alto riesgo.""",
        False,
        "no hay informacion geografica en el dataset",
    ),
]

fallos = 0
print("=" * 70)
print("  REGRESION DEL AUDITOR")
print("=" * 70)

for nombre, texto, esperado_fiable, motivo in CASOS:
    aud = auditar(texto, EXPEDIENTE, LOTE)
    ok = aud["fiable"] == esperado_fiable
    marca = "OK  " if ok else "FALLO"
    if not ok:
        fallos += 1
    print(f"\n[{marca}] {nombre}")
    print(f"        esperado: {'FIABLE' if esperado_fiable else 'NO FIABLE'} | "
          f"obtenido: {aud['veredicto']}")
    print(f"        motivo historico: {motivo}")
    if not ok:
        print(f"        conceptos: {aud['conceptos_inventados']}")
        print(f"        ids inventados: {aud['ids_inventados']} | "
              f"fuera: {aud['ids_fuera_expediente']}")

# ----------------------------------------------------------------------
print("\n" + "=" * 70)
print("  EXTRACCION DE IDENTIFICADORES")
print("=" * 70)
pruebas_id = [
    ("| 156 | 1.0000 |", {156}, "celda de tabla"),
    ("CASO 352", {352}, "encabezado de caso"),
    ("Transacción 0 tiene un importe", {0}, "prosa"),
    ("probabilidad del 100%", set(), "porcentaje, no id"),
    ("Se han identificado 4 casos", set(), "recuento, no id"),
    ("V14 = -9.151", set(), "nombre de variable, no id"),
    ("probabilidad 0.9989", set(), "decimal, no id"),
]
for texto, esperado, desc in pruebas_id:
    obtenido = ids_citados(texto)
    ok = obtenido == esperado
    if not ok:
        fallos += 1
    print(f"  [{'OK  ' if ok else 'FALLO'}] {desc:<28} "
          f"{texto[:34]!r:<38} -> {sorted(obtenido)}")

# ----------------------------------------------------------------------
print("\n" + "=" * 70)
print("  RECUENTO DE VEREDICTOS")
print("=" * 70)
inv = """CASO 156
Analisis del caso.
VEREDICTO: CONFIRMADO

CASO 34
Analisis del caso.
VEREDICTO: CONFIRMADO

CASO 352
Analisis del caso.
VEREDICTO: DESCARTADO
"""
v = veredictos_por_caso(inv)
esperado = {156: "CONFIRMADO", 34: "CONFIRMADO", 352: "DESCARTADO"}
ok = v == esperado
if not ok:
    fallos += 1
print(f"  [{'OK  ' if ok else 'FALLO'}] mapea caso -> veredicto: {v}")

# ----------------------------------------------------------------------
print("\n" + "=" * 70)
if fallos:
    print(f"  {fallos} PRUEBAS FALLIDAS")
    sys.exit(1)
print("  Todas las pruebas pasan.")
print("=" * 70)
