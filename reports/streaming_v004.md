# Informe de ventana 4

- Transacciones: 1434
- Casos: 4

# Informe Final de Fraude

## Resumen Ejecutivo

1. Se han identificado cuatro casos con un alto nivel de riesgo y probabilidad de fraude del 100% o muy cercana a ella.
2. Todos los casos presentan importes bajos, lo que sugiere posibles pruebas preliminares antes de transacciones mayores.
3. Las variables V14, V12 y V4 son las más indicativas de fraude en todos los casos.

## Tabla de Casos Priorizados

| Caso | Importe  | Veredicto    | Acción Recomendada |
|------|----------|--------------|---------------------|
| 1    | 0.00 EUR | ALTO         | Bloquear tarjeta     |
| 2    | 1.59 EUR | ALTO         | Contactar con el cliente |
| 3    | 1.59 EUR | ALTO         | Contactar con el cliente |
| 4    | 0.00 EUR | ALTO         | Bloquear tarjeta     |

## Explicación del Investigador

**Caso 1:**
El detector considera esta transacción sospechosa debido a su importe de 0.00 EUR y a los valores atípicos en las variables V14, V12, V4 y V10, que son indicadores significativos hacia el fraude según el modelo entrenado. Estas variables presentan patrones anómalos que empujan la probabilidad de fraude al máximo nivel posible.

**Caso 2:**
El detector considera este caso como de alto riesgo y con probabilidad de fraude del 100%, principalmente debido a valores atípicos en las variables V14, V4 y V12 que empujan la transacción hacia el fraude. Además, el importe de 1,59 EUR es significativamente menor al importe medio del lote (88,63 EUR), lo cual puede indicar una prueba preliminar con tarjetas no autorizadas antes de realizar cargos mayores.

**Caso 3:**
El detector considera sospechosa esta transacción de 1,59 EUR debido a valores atípicos en las variables V14 (-8,486) y V4 (5,343), que empujan fuertemente hacia la clasificación de fraude. Además, el valor bajo en V12 (-3,986) también contribuye significativamente a esta conclusión. Aunque hay un contrapunto moderado proporcionado por la variable V1 (1,261), los factores que apuntan hacia el fraude son dominantes y llevan al sistema a etiquetar este pago como de alto riesgo.

**Caso 4:**
El detector considera este caso muy sospechoso debido a que presenta valores atípicos en las variables V14 y V12, con valores de -8.636 y -3.978 respectivamente, lo que empuja significativamente la probabilidad hacia el fraude. Además, el valor positivo moderado en V4 (5.925) también contribuye a esta clasificación. Aunque hay un ligero contrapeso por parte de la variable V8 con un valor de 0.865 que tiende a descontar algo del riesgo, el importe muy bajo de 0.00 EUR sugiere una posible prueba de tarjeta robada antes de realizar cargos mayores.

## Nota de Fiabilidad

Este informe se basa en los datos verificados proporcionados por el detector y no incluye información adicional externa. La tabla contiene exactamente cuatro casos, numerados del 1 al 4, sin omitir ninguno.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 0.00 | 17.1h | Sin veredicto | Revisar manualmente |
| 2 | 1.59 | 17.1h | Sin veredicto | Revisar manualmente |
| 3 | 1.59 | 17.1h | Sin veredicto | Revisar manualmente |
| 4 | 0.00 | 17.1h | Sin veredicto | Revisar manualmente |

**4 casos en el expediente**: 0 confirmados, 0 descartados, 4 sin veredicto.
