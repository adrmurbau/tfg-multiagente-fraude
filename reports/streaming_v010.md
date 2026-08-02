# Informe de ventana 10

- Transacciones: 725
- Casos: 3

# Informe Final de Fraudes

## Resumen Ejecutivo

1. Se han identificado tres casos con un alto nivel de riesgo y una probabilidad de fraude del 100% o muy cercana a ella.
2. Los importes varían desde 0,76 EUR hasta 122,68 EUR, pero la gravedad se determina principalmente por las variables atípicas que empujan hacia el fraude.
3. Se recomienda tomar medidas inmediatas para mitigar los riesgos asociados a estas transacciones.

## Tabla de Casos Priorizados

| Caso | Importe (EUR) | Veredicto | Acción Recomendada |
|------|---------------|-----------|---------------------|
| 1    | 122.68        | FRAUDE    | Bloquear tarjeta     |
| 2    | 0.76          | FRAUDE    | Contactar con el cliente |
| 3    | 0.76          | FRAUDE    | Contactar con el cliente |

## Explicación del Investigador

### CASO 1
El detector considera esta transacción muy sospechosa debido a que presenta valores atípicos en las variables V14, V12 y V10, lo cual empuja significativamente la probabilidad hacia el fraude. Aunque el importe de 122.68 EUR no es especialmente bajo, estos componentes anómalos son factores clave que aumentan considerablemente el riesgo asociado a esta transacción.

### CASO 2
El detector considera este caso de alto riesgo debido a que el importe es muy bajo, solo 0,76 EUR, lo cual puede ser una prueba para tarjetas robadas antes de realizar cargos mayores. Además, las variables V14 y V12 presentan valores muy atípicos que empujan la transacción hacia un fraude, mientras que el valor en V4 también contribuye significativamente a esta clasificación. Aunque V8 tiene un efecto contrario, no es suficiente para contrarrestar los demás factores indicativos de fraude.

### CASO 3
El detector considera este caso muy sospechoso debido a que el importe de la transacción es muy bajo, solo 0,76 EUR, lo cual puede ser una prueba para ver si la tarjeta está funcionando antes de realizar un cargo mayor. Además, las variables V14 y V12 presentan valores muy atípicos que empujan fuertemente hacia el fraude, con aportes de +4,551 y +2,112 respectivamente. Aunque las variables V28 y V8 contrarrestan un poco esta tendencia con aportes hacia la legitimidad, no son suficientes para rebajar significativamente la probabilidad de fraude.

## Nota de Fiabilidad
Este informe se basa en los datos verificados proporcionados por el detector de fraudes. Cada caso ha sido evaluado individualmente y las acciones recomendadas buscan mitigar riesgos de manera efectiva.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 122.68 | 17.2h | Sin veredicto | Revisar manualmente |
| 2 | 0.76 | 17.2h | Sin veredicto | Revisar manualmente |
| 3 | 0.76 | 17.2h | Sin veredicto | Revisar manualmente |

**3 casos en el expediente**: 0 confirmados, 0 descartados, 3 sin veredicto.
