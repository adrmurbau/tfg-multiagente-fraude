# Informe de ventana 1

- Transacciones: 1476
- Casos: 3

# Informe Final de Casos de Fraude

## Resumen Ejecutivo

1. Se han identificado tres casos con una probabilidad de fraude del 100% y un nivel de riesgo ALTO.
2. Los importes varían desde 0,77 EUR hasta 94,82 EUR, siendo todos ellos sospechosos por sus valores atípicos en las variables clave.
3. Se recomienda tomar medidas inmediatas para mitigar el potencial fraude en estos casos.

## Tabla de Casos Priorizados

| Caso | Importe (EUR) | Veredicto | Acción Recomendada |
|------|---------------|-----------|---------------------|
| 1    | 1.18          | ALTO      | Bloquear tarjeta     |
| 2    | 94.82         | ALTO      | Contactar con el cliente |
| 3    | 0.77          | ALTO      | Bloquear tarjeta     |

## Explicación del Investigador

**Caso 1:**
El detector considera este caso muy sospechoso debido a que el importe de la transacción es muy bajo, solo 1.18 EUR, lo cual puede indicar una prueba preliminar con tarjetas robadas antes de realizar cargos mayores. Además, las variables V14 (-9.151), V12 (-6.151), V4 (6.009) y V10 (-4.063) presentan valores atípicos que empujan la transacción hacia el fraude, según su aporte al modelo de detección.

**Caso 2:**
El detector considera este caso de alto riesgo debido a que el importe de 94,82 EUR es significativamente mayor en comparación con los montos típicos del lote y presenta valores atípicos en las variables V14 (-7,036), V12 (-5,298) y V10 (-4,919). Estas variables muestran patrones que son inusuales y potencialmente indicativos de comportamientos fraudulentos. Además, la variable V4 (3,248) también contribuye al riesgo, aunque en menor medida, reforzando así la probabilidad de fraude del 100%.

**Caso 3:**
El detector considera este caso sospechoso debido a un importe muy bajo de solo 0,77 EUR y valores atípicos en las variables V14 (-11,272), V12 (-6,888) y V10 (-4,851), que son indicadores significativos hacia el fraude. Además, la variable V4 (7,284) también contribuye de manera notable a esta clasificación. Estos factores juntos hacen que la transacción sea considerada de alto riesgo por el sistema.

## Nota de Fiabilidad

Este informe se basa en los datos verificados proporcionados y no incluye información adicional fuera del dataset disponible. La recomendación es tomar medidas inmediatas para mitigar el potencial fraude identificado en estos casos.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 1.18 | 16.6h | Sin veredicto | Revisar manualmente |
| 2 | 94.82 | 16.7h | Sin veredicto | Revisar manualmente |
| 3 | 0.77 | 16.6h | Sin veredicto | Revisar manualmente |

**3 casos en el expediente**: 0 confirmados, 0 descartados, 3 sin veredicto.
