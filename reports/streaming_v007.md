# Informe de ventana 7

- Transacciones: 1419
- Casos: 2

# Informe Final de Fraude

## Resumen Ejecutivo

- Se han identificado dos casos con alta probabilidad de ser fraudes.
- Ambos casos presentan importes muy bajos y patrones atípicos en las variables clave que indican riesgo elevado.
- Se recomienda tomar medidas inmediatas para mitigar el potencial fraude.

## Tabla de Casos Priorizados

| Caso | Importe  | Veredicto | Acción Recomendada |
|------|----------|-----------|---------------------|
| 1    | 1.10 EUR | ALTO      | Bloquear tarjeta     |
| 2    | 2.00 EUR | ALTO      | Bloquear tarjeta     |

## Explicación del Investigador

**Caso 1:**
El detector considera este caso muy sospechoso debido a que el importe de la transacción es muy bajo, solo 1.10 euros, lo cual puede ser un indicativo de prueba para tarjetas robadas antes de realizar cargos mayores. Además, las variables V14 y V12 presentan valores muy atípicos que empujan fuertemente hacia una clasificación de fraude, mientras que el valor moderado en la variable V28 tiende a contrarrestarlo ligeramente, pero no es suficiente para rebajar significativamente el riesgo.

**Caso 2:**
El detector considera este caso sospechoso debido a que el importe de la transacción es muy bajo, solo 2 euros, lo cual puede ser una prueba para ver si la tarjeta está funcionando antes de realizar cargos mayores. Además, las variables V14, V12 y V10 presentan valores muy atípicos que empujan hacia un fraude, mientras que el valor moderado en V8 es el único factor que resta algo de riesgo a la transacción.

## Nota de Fiabilidad

Este informe se basa únicamente en los datos proporcionados por el detector y no incluye información adicional sobre el cliente o las circunstancias específicas. Se recomienda tomar medidas inmediatas para mitigar cualquier potencial fraude identificado.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 1.10 | 17.6h | Sin veredicto | Revisar manualmente |
| 2 | 2.00 | 17.6h | Sin veredicto | Revisar manualmente |

**2 casos en el expediente**: 0 confirmados, 0 descartados, 2 sin veredicto.
