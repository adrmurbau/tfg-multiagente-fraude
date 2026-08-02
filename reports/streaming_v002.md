# Informe de ventana 2

- Transacciones: 781
- Casos: 1

# Informe de Análisis de Transacciones

## Resumen Ejecutivo

El análisis revela que todas las transacciones en este conjunto de datos se clasifican como de bajo riesgo, con la excepción del caso 1, que es considerado altamente sospechoso. La mayoría de los casos presentan importes bajos y variables atípicas que empujan hacia una mayor probabilidad de fraude, pero otros factores contribuyen a disminuir este riesgo. El caso 46 destaca por su importe bajo (11.80 EUR) y valores atípicos en las variables V4, V11, V14 y V10 que mantienen el nivel de riesgo bajo.

## Tabla Priorizada

|ID | Importe (EUR) | Nivel de Riesgo |
|---|---------------|-----------------|
| 1 | 1.18          | ALTO            |
| 26| 100.07        | BAJO            |
| 46| 11.80         | BAJO            |

## Casos con Acción Recomendada

### CASO 1
- **Importe:** 1.18 EUR
- **Nivel de Riesgo:** ALTO
- **Explicación:** El importe muy bajo y valores atípicos en las variables V14, V12 y V10 empujan hacia una clasificación de alta probabilidad de fraude.

### CASO 26
- **Importe:** 100.07 EUR
- **Nivel de Riesgo:** BAJO
- **Explicación:** Importe moderado con valores atípicos en las variables V4, V11 y V28 que empujan hacia una clasificación de baja probabilidad de fraude.

### CASO 46
- **Importe:** 11.80 EUR
- **Nivel de Riesgo:** BAJO
- **Explicación:** Importe bajo con valores atípicos en las variables V4, V11, V14 y V10 que mantienen el nivel de riesgo bajo.

## Nota de Fiabilidad

El análisis se basó únicamente en los datos proporcionados y no incluye información adicional sobre el historial del cliente o detalles específicos de la transacción. La fiabilidad del modelo depende de su capacidad para identificar patrones atípicos que puedan indicar fraude, pero también puede generar falsas alarmas debido a la naturaleza anónima y limitada de los datos.

---

Este informe proporciona una visión general de las transacciones analizadas, destacando aquellos casos que requieren mayor atención por su nivel de riesgo.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 1.18 | 16.6h | Sin veredicto | Revisar manualmente |
| 2 | 2.22 | 16.6h | Sin veredicto | Revisar manualmente |
| 3 | 0.77 | 16.5h | Sin veredicto | Revisar manualmente |
| 4 | 302.65 | 16.6h | Sin veredicto | Revisar manualmente |
| 5 | 1791.12 | 16.5h | Sin veredicto | Revisar manualmente |
| 6 | 750.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 7 | 206.99 | 16.5h | Sin veredicto | Revisar manualmente |
| 8 | 183.57 | 16.5h | Sin veredicto | Revisar manualmente |
| 9 | 219.15 | 16.6h | Sin veredicto | Revisar manualmente |
| 10 | 1024.08 | 16.6h | Sin veredicto | Revisar manualmente |
| 11 | 117.80 | 16.6h | Sin veredicto | Revisar manualmente |
| 12 | 223.96 | 16.6h | Sin veredicto | Revisar manualmente |
| 13 | 299.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 14 | 32.93 | 16.5h | Sin veredicto | Revisar manualmente |
| 15 | 3.15 | 16.5h | Sin veredicto | Revisar manualmente |
| 16 | 480.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 17 | 214.08 | 16.5h | Sin veredicto | Revisar manualmente |
| 18 | 35.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 19 | 199.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 20 | 338.97 | 16.5h | Sin veredicto | Revisar manualmente |
| 21 | 3.54 | 16.5h | Sin veredicto | Revisar manualmente |
| 22 | 4.99 | 16.5h | Sin veredicto | Revisar manualmente |
| 23 | 49.98 | 16.6h | Sin veredicto | Revisar manualmente |
| 24 | 50.00 | 16.5h | Sin veredicto | Revisar manualmente |
| 25 | 2088.00 | 16.5h | Sin veredicto | Revisar manualmente |
| 26 | 100.07 | 16.5h | Sin veredicto | Revisar manualmente |
| 27 | 0.89 | 16.6h | Sin veredicto | Revisar manualmente |
| 28 | 2.69 | 16.6h | Sin veredicto | Revisar manualmente |
| 29 | 3.59 | 16.5h | Sin veredicto | Revisar manualmente |
| 30 | 3.04 | 16.6h | Sin veredicto | Revisar manualmente |
| 31 | 5.99 | 16.5h | Sin veredicto | Revisar manualmente |
| 32 | 3.58 | 16.5h | Sin veredicto | Revisar manualmente |
| 33 | 11.50 | 16.5h | Sin veredicto | Revisar manualmente |
| 34 | 664.35 | 16.6h | Sin veredicto | Revisar manualmente |
| 35 | 44.22 | 16.6h | Sin veredicto | Revisar manualmente |
| 36 | 9.99 | 16.5h | Sin veredicto | Revisar manualmente |
| 37 | 25.00 | 16.5h | Sin veredicto | Revisar manualmente |
| 38 | 750.90 | 16.6h | Sin veredicto | Revisar manualmente |
| 39 | 59.29 | 16.5h | Sin veredicto | Revisar manualmente |
| 40 | 3.99 | 16.5h | Sin veredicto | Revisar manualmente |
| 41 | 390.65 | 16.6h | Sin veredicto | Revisar manualmente |
| 42 | 1.98 | 16.5h | Sin veredicto | Revisar manualmente |
| 43 | 39.92 | 16.5h | Sin veredicto | Revisar manualmente |
| 44 | 37.93 | 16.6h | Sin veredicto | Revisar manualmente |
| 45 | 493.25 | 16.5h | Sin veredicto | Revisar manualmente |
| 46 | 11.80 | 16.5h | Sin veredicto | Revisar manualmente |
| 47 | 9.49 | 16.6h | Sin veredicto | Revisar manualmente |
| 48 | 2687.48 | 16.6h | Sin veredicto | Revisar manualmente |
| 49 | 1.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 50 | 16.47 | 16.5h | Sin veredicto | Revisar manualmente |
| 51 | 17.99 | 16.6h | Sin veredicto | Revisar manualmente |
| 52 | 15.81 | 16.6h | Sin veredicto | Revisar manualmente |
| 53 | 322.39 | 16.6h | Sin veredicto | Revisar manualmente |
| 54 | 160.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 55 | 12.31 | 16.6h | Sin veredicto | Revisar manualmente |
| 56 | 21.58 | 16.5h | Sin veredicto | Revisar manualmente |
| 57 | 74.91 | 16.5h | Sin veredicto | Revisar manualmente |
| 58 | 259.43 | 16.5h | Sin veredicto | Revisar manualmente |
| 59 | 1.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 60 | 24.99 | 16.5h | Sin veredicto | Revisar manualmente |

**60 casos en el expediente**: 0 confirmados, 0 descartados, 60 sin veredicto.
