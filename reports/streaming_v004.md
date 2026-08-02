# Informe de ventana 4

- Transacciones: 1434
- Casos: 4

# Informe Final sobre Casos de Fraude

## Resumen Ejecutivo

1. Se han identificado cuatro casos con un alto nivel de riesgo y una probabilidad de fraude del 100% o muy cercana a ella.
2. Todos los casos muestran patrones atípicos en las variables anónimas que indican actividades potencialmente fraudulentas, independientemente del importe transaccionado.
3. Se recomienda tomar medidas inmediatas para mitigar el riesgo asociado con estas transacciones.

## Tabla de Casos Priorizados

|Caso | Importe  | Veredicto   | Acción Recomendada |
|-----|---------|------------|-------------------|
|1    | 0.00 EUR| FRAUDE ALTO | Bloquear tarjeta   |
|2    | 1.59 EUR| FRAUDE ALTO | Contactar con el cliente |
|3    | 1.59 EUR| FRAUDE ALTO | Contactar con el cliente |
|4    | 0.00 EUR| FRAUDE ALTO | Bloquear tarjeta   |

## Explicación del Investigador

**Caso 1:** El detector identifica este caso como un fraude alto riesgo debido a valores atípicos en las variables V14, V12, V4 y V10. Aunque el importe es de 0.00 EUR, los patrones inusuales sugieren posibles actividades fraudulentas.

**Caso 2:** Se considera sospechoso debido a valores atípicos en las variables V14, V4 y V12 que empujan fuertemente hacia el fraude. El importe de 1.59 EUR es muy bajo comparado con el importe medio del lote (88.63 EUR), lo que puede indicar una prueba preliminar antes de un cargo mayor.

**Caso 3:** Se identifica como sospechoso debido a valores atípicos en las variables V14 y V4, junto con un valor bajo en V12. Aunque la variable V1 disminuye ligeramente la probabilidad de fraude, el impacto total es hacia el fraude.

**Caso 4:** Se considera muy sospechoso debido a valores atípicos en las variables V14 y V12, con un valor alto en V4. A pesar del importe bajo (0.00 EUR), los patrones indican actividades potencialmente fraudulentas.

## Nota de Fiabilidad

Este informe se basa únicamente en la información proporcionada por el detector de fraudes y no incluye datos adicionales sobre el cliente o las transacciones. La recomendación es tomar medidas inmediatas para mitigar los riesgos identificados.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 0.00 | 17.1h | Sin veredicto | Revisar manualmente |
| 2 | 1.59 | 17.1h | Sin veredicto | Revisar manualmente |
| 3 | 1.59 | 17.1h | Sin veredicto | Revisar manualmente |
| 4 | 0.00 | 17.1h | Sin veredicto | Revisar manualmente |

**4 casos en el expediente**: 0 confirmados, 0 descartados, 4 sin veredicto.
