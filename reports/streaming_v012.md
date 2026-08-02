# Informe de ventana 12

- Transacciones: 692
- Casos: 1

# Informe de Análisis de Transacciones

## Resumen Ejecutivo

El análisis realizado sobre las 60 transacciones identificó un caso con alta probabilidad de ser fraudulento (ID 1) y varios casos con baja probabilidad pero que requieren vigilancia adicional debido a características atípicas. El importe medio del lote es de 86.73 EUR, lo cual se utiliza como referencia para evaluar la normalidad de cada transacción.

## Tabla Priorizada

|ID |Probabilidad de Fraude |Nivel de Riesgo |Importe (EUR) |
|---|-----------------------|----------------|-------------|
|1  |1.0000                 |ALTO            |0.00         |
|2  |0.2060                 |BAJO            |1059.28      |

## Casos con Acción Recomendada

### CASO 1
El detector considera altamente sospechoso este caso debido a que presenta un importe de transacción muy bajo, específicamente 0.00 EUR, lo cual es común en intentos preliminares de prueba con tarjetas robadas antes de realizar cargos mayores. Además, las variables V14, V4 y V12 muestran valores atípicamente bajos o altos que empujan la transacción hacia el fraude, mientras que V10 también contribuye significativamente a esta clasificación.

### CASO 2
El detector considera sospechosa la transacción de 1059.28 EUR debido a valores atípicos en las variables V4 y V12 que empujan hacia un riesgo de fraude, mientras que el valor en V11 sugiere comportamiento más legítimo. La hora del día también puede estar influyendo en la evaluación, aunque no se especifica su impacto directo.

## Nota de Fiabilidad
El análisis ha sido realizado basándose únicamente en los datos proporcionados y las explicaciones generadas por el detector de fraudes. Sin analisis disponible para otros casos, no se han añadido interpretaciones adicionales ni suposiciones sobre la naturaleza de las transacciones o variables específicas.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 0.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 2 | 1059.28 | 17.4h | Sin veredicto | Revisar manualmente |
| 3 | 29.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 4 | 106.04 | 17.4h | Sin veredicto | Revisar manualmente |
| 5 | 17.33 | 17.4h | Sin veredicto | Revisar manualmente |
| 6 | 246.46 | 17.4h | Sin veredicto | Revisar manualmente |
| 7 | 134.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 8 | 17.50 | 17.4h | Sin veredicto | Revisar manualmente |
| 9 | 49.90 | 17.3h | Sin veredicto | Revisar manualmente |
| 10 | 91.74 | 17.4h | Sin veredicto | Revisar manualmente |
| 11 | 145.82 | 17.4h | Sin veredicto | Revisar manualmente |
| 12 | 44.96 | 17.4h | Sin veredicto | Revisar manualmente |
| 13 | 49.95 | 17.4h | Sin veredicto | Revisar manualmente |
| 14 | 212.36 | 17.4h | Sin veredicto | Revisar manualmente |
| 15 | 1.29 | 17.4h | Sin veredicto | Revisar manualmente |
| 16 | 12.31 | 17.4h | Sin veredicto | Revisar manualmente |
| 17 | 1618.42 | 17.4h | Sin veredicto | Revisar manualmente |
| 18 | 247.04 | 17.4h | Sin veredicto | Revisar manualmente |
| 19 | 400.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 20 | 10.00 | 17.3h | Sin veredicto | Revisar manualmente |
| 21 | 1299.23 | 17.4h | Sin veredicto | Revisar manualmente |
| 22 | 20.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 23 | 45.89 | 17.4h | Sin veredicto | Revisar manualmente |
| 24 | 5.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 25 | 11.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 26 | 298.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 27 | 1.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 28 | 22.44 | 17.4h | Sin veredicto | Revisar manualmente |
| 29 | 12.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 30 | 10.54 | 17.4h | Sin veredicto | Revisar manualmente |
| 31 | 444.67 | 17.4h | Sin veredicto | Revisar manualmente |
| 32 | 120.21 | 17.4h | Sin veredicto | Revisar manualmente |
| 33 | 107.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 34 | 6.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 35 | 1.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 36 | 22.76 | 17.4h | Sin veredicto | Revisar manualmente |
| 37 | 592.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 38 | 10.77 | 17.4h | Sin veredicto | Revisar manualmente |
| 39 | 11.50 | 17.4h | Sin veredicto | Revisar manualmente |
| 40 | 380.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 41 | 221.74 | 17.4h | Sin veredicto | Revisar manualmente |
| 42 | 367.43 | 17.4h | Sin veredicto | Revisar manualmente |
| 43 | 4.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 44 | 461.24 | 17.4h | Sin veredicto | Revisar manualmente |
| 45 | 33.79 | 17.4h | Sin veredicto | Revisar manualmente |
| 46 | 458.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 47 | 252.58 | 17.4h | Sin veredicto | Revisar manualmente |
| 48 | 30.58 | 17.4h | Sin veredicto | Revisar manualmente |
| 49 | 1.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 50 | 40.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 51 | 34.66 | 17.4h | Sin veredicto | Revisar manualmente |
| 52 | 28.75 | 17.4h | Sin veredicto | Revisar manualmente |
| 53 | 541.75 | 17.4h | Sin veredicto | Revisar manualmente |
| 54 | 4.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 55 | 26.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 56 | 237.16 | 17.4h | Sin veredicto | Revisar manualmente |
| 57 | 42.81 | 17.4h | Sin veredicto | Revisar manualmente |
| 58 | 660.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 59 | 402.75 | 17.4h | Sin veredicto | Revisar manualmente |
| 60 | 1.00 | 17.4h | Sin veredicto | Revisar manualmente |

**60 casos en el expediente**: 0 confirmados, 0 descartados, 60 sin veredicto.
