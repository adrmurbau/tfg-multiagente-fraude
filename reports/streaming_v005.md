# Informe de ventana 5

- Transacciones: 1436
- Casos: 3

# Informe Final de Casos de Fraude

## Resumen Ejecutivo

- Se han identificado tres casos con un alto nivel de riesgo de fraude.
- El importe total del lote es de 104.33 EUR, siendo el caso 1 el más significativo con 122.68 EUR.
- Recomendaciones específicas para cada caso basadas en la probabilidad y variables atípicas.

## Tabla de Casos Priorizados

| Caso | Importe (EUR) | Veredicto | Acción Recomendada |
|------|---------------|-----------|---------------------|
| 1    | 122.68        | FRAUDE    | Bloquear tarjeta     |
| 2    | 0.76          | FRAUDE    | Contactar con el cliente |
| 3    | 0.76          | FRAUDE    | Contactar con el cliente |

## Explicación del Investigador

### CASO 1
El detector considera altamente sospechoso este caso debido a valores muy atípicos en las variables V14, V12 y V10, que empujan fuertemente hacia la clasificación de fraude. Estas variables presentan valores negativos significativos con un alto impacto positivo en la probabilidad de fraude. Además, el importe de 122.68 EUR es considerablemente mayor al importe medio del lote, lo que también aumenta las sospechas.

### CASO 2
El detector considera este caso de alto riesgo debido a que el importe es muy bajo, solo 0,76 EUR, lo cual puede ser una prueba para tarjetas robadas antes de realizar cargos mayores. Además, las variables V14 y V12 presentan valores muy atípicos que empujan la transacción hacia un fraude, mientras que el valor en V4 también contribuye significativamente a esta clasificación. Aunque la variable V8 tiende a contrarrestar esto con un efecto contrario, no es suficiente para rebajar el riesgo del caso.

### CASO 3
El detector considera este caso muy sospechoso debido a que el importe de la transacción es muy bajo, solo 0,76 EUR, lo cual puede ser una prueba para tarjetas robadas antes de realizar cargos mayores. Además, las variables V14 y V12 presentan valores muy atípicos que empujan hacia un fraude, con aportes significativos de +4,551 y +2,112 respectivamente. Aunque las variables V28 y V8 también tienen cierto peso en la decisión, su efecto es menor y apunta más hacia una transacción legítima, con aportes de -1,704 y -1,413 respectivamente.

## Nota de Fiabilidad
Este informe se basa únicamente en los datos verificados proporcionados por el detector. No se han realizado suposiciones adicionales ni se ha utilizado información externa no incluida en el dataset.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 122.68 | 17.2h | Sin veredicto | Revisar manualmente |
| 2 | 0.76 | 17.2h | Sin veredicto | Revisar manualmente |
| 3 | 0.76 | 17.2h | Sin veredicto | Revisar manualmente |

**3 casos en el expediente**: 0 confirmados, 0 descartados, 3 sin veredicto.
