# Informe de ventana 1

- Transacciones: 1476
- Casos: 3

# Informe Final de Fraudes

## Resumen Ejecutivo

1. Se han identificado tres casos con un alto nivel de riesgo y una probabilidad de fraude del 100%.
2. Los importes varían desde 0,77 EUR hasta 94,82 EUR, siendo el importe medio del lote de 103,73 EUR.
3. Todas las transacciones presentan valores atípicos en variables clave que indican un alto riesgo de fraude.

## Tabla de Casos Priorizados

| Caso | Importe (EUR) | Veredicto | Acción Recomendada |
|------|---------------|-----------|---------------------|
| 1    | 1.18          | ALTO      | Bloquear tarjeta     |
| 2    | 94.82         | ALTO      | Contactar con el cliente |
| 3    | 0.77          | ALTO      | Bloquear tarjeta     |

## Explicación del Investigador

**Caso 1:**
El detector considera esta transacción muy sospechosa debido a que su importe de 1,18 EUR es significativamente menor al importe medio del lote (103,73 EUR), lo cual puede indicar una prueba de tarjeta robada. Además, las variables V14 (-9,151) y V12 (-6,151) presentan valores muy atípicos que empujan fuertemente la decisión hacia el fraude, mientras que V4 (6,009) y V10 (-4,063) también contribuyen de manera importante a esta clasificación.

**Caso 2:**
El detector considera altamente sospechosa esta transacción por un importe de 94.82 EUR, principalmente debido a valores atípicos en las variables V14 (-7.036), V12 (-5.298) y V10 (-4.919), que empujan significativamente la probabilidad hacia el fraude. Estas variables anónimas presentan patrones poco comunes que, junto con el importe considerable de la transacción, hacen que sea considerada riesgosa.

**Caso 3:**
El detector considera sospechoso este caso debido a un importe muy bajo de solo 0,77 EUR y valores atípicos en las variables V14 (-11,272), V12 (-6,888) y V10 (-4,851), que son indicadores significativos hacia el fraude. Además, la variable V4 (7,284) también contribuye de manera notable a esta clasificación. Estos factores juntos hacen que la transacción sea considerada de alto riesgo por el sistema.

## Nota de Fiabilidad

Este informe se basa en los datos verificados proporcionados por el detector de fraudes y no incluye información adicional sobre el cliente o las circunstancias específicas del fraude. La recomendación es tomar medidas inmediatas para mitigar el riesgo identificado en cada caso.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 1.18 | 16.6h | Sin veredicto | Revisar manualmente |
| 2 | 94.82 | 16.7h | Sin veredicto | Revisar manualmente |
| 3 | 0.77 | 16.6h | Sin veredicto | Revisar manualmente |

**3 casos en el expediente**: 0 confirmados, 0 descartados, 3 sin veredicto.
