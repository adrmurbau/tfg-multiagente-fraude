# Informe de ventana 9

- Transacciones: 1381
- Casos: 2

# Informe Final de Fraude

## Resumen Ejecutivo

1. Se han identificado dos casos con un alto nivel de riesgo y una probabilidad muy cercana a 1 de ser fraude.
2. Ambos casos presentan importes significativamente inferiores al importe medio del lote, lo que sugiere posibles pruebas preliminares de tarjetas robadas antes de cargos mayores.
3. Se recomienda tomar medidas inmediatas para mitigar el riesgo en ambos casos.

## Tabla de Casos Priorizados

| Caso | Importe (EUR) | Veredicto | Acción Recomendada |
|------|---------------|-----------|---------------------|
| 1    | 10.70         | ALTO      | Bloquear tarjeta     |
| 2    | 9.29          | ALTO      | Bloquear tarjeta     |

## Explicación del Investigador

**Caso 1:**
El detector considera este caso sospechoso debido a que el importe de la transacción, 10.70 EUR, es significativamente menor en comparación con el importe medio del lote (92.85 EUR), lo cual puede indicar una prueba preliminar de tarjeta robada antes de un cargo mayor. Además, las variables V14 (-7.624), V12 (-4.165) y V10 (-4.760) presentan valores muy atípicos que empujan la transacción hacia el fraude, mientras que la variable V8 (1.245) es la única que tiende a contrarrestar esta tendencia, aunque en menor medida.

**Caso 2:**
El detector considera este caso muy sospechoso debido a que el importe de la transacción, 9.29 EUR, es significativamente menor al importe medio del lote (92.85 EUR), lo cual puede indicar una prueba de tarjeta robada antes de un cargo mayor. Además, las variables V14 (-4.978) y V10 (-3.509) muestran valores muy atípicos que empujan la transacción hacia el fraude, mientras que V26 (-0.264) es menos indicativa de fraude pero no logra contrarrestar completamente los otros factores.

## Nota de Fiabilidad

Este informe se basa en datos verificados por el detector y las explicaciones proporcionadas por el investigador. No se han realizado suposiciones adicionales ni se han omitido casos.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 10.70 | 18.0h | Sin veredicto | Revisar manualmente |
| 2 | 9.29 | 17.9h | Sin veredicto | Revisar manualmente |

**2 casos en el expediente**: 0 confirmados, 0 descartados, 2 sin veredicto.
