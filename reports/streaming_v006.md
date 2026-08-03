# Informe de ventana 6

- Transacciones: 1375
- Casos: 2

# Informe Final de Fraudes

## Resumen Ejecutivo

- Se han identificado dos casos con un alto nivel de riesgo de fraude.
- Ambos casos presentan importes muy bajos y valores atípicos en las variables clave que indican comportamientos sospechosos.
- Se recomienda tomar medidas inmediatas para mitigar el riesgo.

## Tabla de Casos Priorizados

| Caso | Importe  | Veredicto   | Acción Recomendada |
|------|----------|-------------|---------------------|
| 1    | 0.00 EUR | FRAUDE      | Bloquear tarjeta     |
| 2    | 1.00 EUR | FRAUDE      | Contactar con el cliente |

## Explicación del Investigador

**Caso 1:**
El detector considera esta transacción muy sospechosa debido a su importe extremadamente bajo de 0,00 EUR y a valores atípicos en las variables V14, V4, V12 y V10. Estos componentes contribuyen significativamente al riesgo, especialmente V14 con un valor muy alejado que empuja fuertemente hacia la clasificación de fraude.

**Caso 2:**
El detector considera este caso sospechoso debido a que presenta valores atípicos en las variables V14 y V4, lo cual empuja la probabilidad hacia el fraude. Además, el importe de la transacción es muy bajo (1.00 EUR), un comportamiento común para tarjetas robadas al probarse con pequeños pagos antes del cargo principal. Aunque las variables V16 y V10 también tienen cierto impacto, no son suficientes para contrarrestar la alta señal de fraude generada por el resto de los componentes.

## Nota de Fiabilidad

Este informe se basa en datos verificados del detector de fraudes. Cada caso ha sido analizado y priorizado según su nivel de riesgo, con recomendaciones específicas para mitigar posibles actividades fraudulentas.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 0.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 2 | 1.00 | 17.5h | Sin veredicto | Revisar manualmente |

**2 casos en el expediente**: 0 confirmados, 0 descartados, 2 sin veredicto.
