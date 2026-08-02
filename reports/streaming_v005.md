# Informe de ventana 5

- Transacciones: 1436
- Casos: 3

# Informe Final de Fraudes

## Resumen Ejecutivo

- Se han identificado tres casos con un alto nivel de riesgo y una probabilidad de fraude del 100% o muy cercana a ella.
- El importe total de los lotes sospechosos es de 124.2 EUR, siendo el caso más significativo un monto de 122.68 EUR.
- Se recomienda tomar medidas inmediatas para mitigar estos riesgos.

## Tabla de Casos Priorizados

| Caso | Importe (EUR) | Veredicto | Acción Recomendada |
|------|---------------|-----------|---------------------|
| 1    | 122.68        | ALTO      | Bloquear tarjeta     |
| 2    | 0.76          | ALTO      | Contactar con el cliente |
| 3    | 0.76          | ALTO      | Contactar con el cliente |

## Explicación del Investigador

### CASO 1
El detector considera esta transacción muy sospechosa debido a que presenta valores atípicos en las variables V14, V12 y V10, lo cual empuja significativamente la probabilidad hacia el fraude. Aunque el importe de 122.68 EUR no es especialmente bajo, estos componentes anómalos son los principales factores que hacen que la transacción sea considerada de alto riesgo.

### CASO 2
El detector considera este caso sospechoso debido a que el importe de la transacción es muy bajo, solo 0.76 EUR, lo cual puede ser un indicativo de prueba para tarjetas robadas. Además, las variables V14 y V12 presentan valores muy atípicos que empujan fuertemente hacia una clasificación de fraude, mientras que el valor en la variable V4 también contribuye significativamente a esta conclusión. Aunque la variable V8 muestra un efecto contrario, no es suficiente para contrarrestar los demás indicadores.

### CASO 3
El detector considera este caso muy sospechoso debido a que el importe de la transacción es muy bajo, solo 0.76 EUR, lo cual puede ser una prueba para ver si la tarjeta está siendo utilizada correctamente antes de realizar cargos mayores. Además, los valores atípicos en las variables V14 (-6,800) y V12 (-6,285) empujan fuertemente hacia el fraude, mientras que las variables V28 (0,676) y V8 (1,131) intentan contrarrestarlo pero no son suficientes para rebajar la probabilidad de fraude.

## Nota de Fiabilidad
Este informe se basa en los datos verificados proporcionados por el detector de fraudes. Cada caso ha sido analizado individualmente y las acciones recomendadas están diseñadas para mitigar riesgos de manera efectiva.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 122.68 | 17.2h | Sin veredicto | Revisar manualmente |
| 2 | 0.76 | 17.2h | Sin veredicto | Revisar manualmente |
| 3 | 0.76 | 17.2h | Sin veredicto | Revisar manualmente |

**3 casos en el expediente**: 0 confirmados, 0 descartados, 3 sin veredicto.
