# Informe de ventana 3

- Transacciones: 695
- Casos: 2

# Informe de Análisis de Transacciones

## Resumen Ejecutivo

El presente informe analiza 60 transacciones según su nivel de riesgo y probabilidad de fraude. Se identifican dos casos con un alto nivel de riesgo, mientras que el resto se clasifica como bajo riesgo. Los casos con alta probabilidad de ser fraudulentos requieren una revisión más detallada para confirmar la autenticidad.

## Tabla Priorizada

|ID |Probabilidad de Fraude |Nivel de Riesgo |Importe (EUR) |
|---|-----------------------|----------------|-------------|
|1  |1.0000                 |ALTO            |94.82        |
|2  |1.0000                 |ALTO            |0.77         |
|3  |0.0085                 |BAJO            |349.51       |
|4  |0.0080                 |BAJO            |200.00       |
|5  |0.0073                 |BAJO            |800.00       |
|6  |0.0015                 |BAJO            |7.57         |
|7  |0.0009                 |BAJO            |310.00       |
|8  |0.0009                 |BAJO            |31.98        |
|9  |0.0006                 |BAJO            |29.60        |
|10 |0.0006                 |BAJO            |6.99         |

## Casos con Acción Recomendada

### CASO 1
El detector considera altamente sospechosa esta transacción por un importe de 94.82 EUR, principalmente debido a valores muy atípicos en las variables V14 (-7.036), V12 (-5.298) y V10 (-4.919), que empujan significativamente la probabilidad hacia el fraude. Además, un valor positivo anómalo en V4 (3.248) contribuye a esta clasificación de riesgo alto.

**Acción recomendada:** Revisar y confirmar la autenticidad de la transacción.

### CASO 2
El detector considera altamente sospechosa esta transacción por su importe muy bajo de 0,77 EUR y los valores atípicos en las variables V14, V12, V4 y V10, que empujan la probabilidad hacia el fraude. Estos factores indican comportamientos poco comunes que son típicos en intentos de prueba con tarjetas no autorizadas antes de realizar cargos mayores.

**Acción recomendada:** Revisar y confirmar la autenticidad de la transacción.

### CASO 3
El detector considera que la transacción de 349.51 EUR es poco probable que sea fraude, ya que las variables V4, V12, V7 y V27 presentan valores que contribuyen a disminuir la probabilidad de ser un caso sospechoso. Aunque el importe es significativamente mayor al importe medio del lote (115.57 EUR), estos componentes anónimos ayudan a mantener el nivel de riesgo en bajo.

**Acción recomendada:** No requiere acción adicional.

### CASO 4
El detector considera que la transacción de 200.00 EUR es ligeramente sospechosa debido a un valor muy atípico en el componente V14, lo cual empuja hacia una mayor probabilidad de fraude. Sin embargo, otros componentes como V1 y V12 contrarrestan esta señal con valores que indican comportamiento legítimo. A pesar de esto, la combinación de estos factores resulta en un nivel de riesgo bajo para este caso.

**Acción recomendada:** No requiere acción adicional.

### CASO 5
El detector considera que la transacción de 800.00 EUR tiene un riesgo bajo, ya que las variables V11, V14 y V12 presentan valores muy bajos que contribuyen a disminuir la probabilidad de fraude. Sin embargo, el importe es significativamente mayor al promedio del lote (115.57 EUR), lo que podría ser un factor que genera cierta preocupación aunque no sea suficiente para elevar el riesgo a nivel alto.

**Acción recomendada:** No requiere acción adicional.

### CASO 6
El detector considera que el caso es ligeramente sospechoso debido a un valor muy atípico en la variable V4, lo cual empuja hacia una mayor probabilidad de fraude. Sin embargo, otros componentes como V10 y V14 contrarrestan este efecto al señalar comportamientos más normales. El importe de 7.57 EUR es bajo, un monto que a menudo se usa para probar tarjetas robadas antes de realizar cargos mayores.

**Acción recomendada:** No requiere acción adicional.

### CASO 7
El detector considera este caso de baja probabilidad de fraude debido a que las variables V4, V7 y V12 presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar del importe considerable de 310.00 EUR, el modelo no identifica patrones o comportamientos atípicos en estas componentes anonimizadas que sugieran riesgo elevado.

**Acción recomendada:** No requiere acción adicional.

### CASO 8
El detector considera este caso de bajo riesgo debido a que las variables V14, V11 y V12 presentan valores que favorecen la clasificación como transacción legítima, junto con un importe relativamente pequeño de 31.98 EUR, lo cual es común en tarjetas no comprometidas.

**Acción recomendada:** No requiere acción adicional.

### CASO 9
El detector considera este caso sospechoso debido a que el importe de la transacción es relativamente bajo, con un valor de 29.60 EUR, lo cual puede indicar una prueba inicial antes de realizar cargos más grandes. Además, las variables V14, V4 y V10 muestran valores que empujan hacia la clasificación como legítima, pero el modelo en su conjunto aún percibe ciertos patrones atípicos que mantienen un nivel bajo de riesgo.

**Acción recomendada:** No requiere acción adicional.

### CASO 10
El detector considera que la transacción de 6.99 EUR tiene un bajo nivel de riesgo, ya que las variables V10, V18 y V23 muestran valores que contribuyen a clasificarla como legítima, con puntuaciones negativas que indican una menor probabilidad de fraude. Sin embargo, el importe es relativamente pequeño en comparación con el importe medio del lote (115.57 EUR), lo cual podría sugerir un intento inicial de prueba antes de realizar cargos mayores.

**Acción recomendada:** No requiere acción adicional.

### CASO 11
El detector considera sospechoso este caso debido a que el importe de la transacción es muy bajo, solo 1.56 EUR, lo cual puede ser un indicativo de prueba para tarjetas robadas antes de realizar cargos mayores. Además, las variables V14 y V4 muestran valores que empujan hacia fraude (+1.865 y +1.247 respectivamente), mientras que V10 y V7 tienen efectos contrarios (-3.935 y -1.613) que minimizan la probabilidad de ser fraudulenta, manteniendo el riesgo en nivel bajo.

**Acción recomendada:** No requiere acción adicional.

### CASO 12
El detector considera este caso de bajo riesgo debido a que las variables V14, V25 y V11 presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar de esto, el importe de 188.73 EUR es mayor al importe medio del lote, lo cual podría ser un factor a tener en cuenta aunque no sea suficiente para elevar el nivel de riesgo.

**Acción recomendada:** No requiere acción adicional.

### CASO 13
El detector considera este caso de bajo riesgo debido a que las variables V11, V12 y V14 presentan valores muy bajos que indican comportamientos típicamente legítimos, mientras que el importe de 28.92 EUR es relativamente pequeño pero no extremadamente bajo en comparación con el importe medio del lote.

**Acción recomendada:** No requiere acción adicional.

### CASO 14
El detector considera este caso de baja probabilidad de fraude debido a que las variables V4, V28 y V11 presentan valores que favorecen la clasificación como transacción legítima. Sin embargo, el importe de 429.89 EUR es significativamente mayor al importe medio del lote (115.57 EUR), lo que podría generar cierta alerta aunque no sea suficiente para elevar el riesgo a un nivel más alto.

**Acción recomendada:** No requiere acción adicional.

### CASO 15
El detector considera sospechoso el caso 15 debido a que la transacción de 264.00 EUR presenta un valor atípico en V4, lo cual empuja hacia una mayor probabilidad de fraude, mientras que otros componentes como V10 y V25 muestran valores que disminuyen esta posibilidad.

**Acción recomendada:** No requiere acción adicional.

### CASO 16
El detector considera este caso de bajo riesgo debido a que las variables V14, V11, V22 y V26 presentan valores que tienden a clasificar la transacción como legítima. A pesar de ello, el importe muy pequeño de 1.98 EUR puede sugerir una prueba inicial con tarjetas robadas antes de realizar cargos mayores.

**Acción recomendada:** No requiere acción adicional.

### CASO 17
El detector considera este caso de bajo riesgo debido a que las variables V14, V11, V12 y V22 presentan valores muy atípicos que empujan la transacción hacia lo legítimo. A pesar del importe considerable de 1035.00 EUR, estas características anómalas en los componentes PCA reducen significativamente las probabilidades de fraude.

**Acción recomendada:** No requiere acción adicional.

### CASO 18
El detector considera que la transacción de 144.00 EUR es poco probable que sea fraudulenta, ya que las variables V12, V1 y V14 presentan valores que contribuyen significativamente a disminuir el riesgo de fraude. Sin embargo, el importe de esta transacción se encuentra dentro del rango típico para casos sospechosos, lo que mantiene un nivel de riesgo bajo pero no nulo.

**Acción recomendada:** No requiere acción adicional.

### CASO 19
El detector considera este caso de bajo riesgo debido a que las variables V11, V14 y V10 presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. Aunque el importe de 258.90 EUR es mayor que el importe medio del lote, estos componentes anónimos reducen considerablemente la probabilidad de fraude.

**Acción recomendada:** No requiere acción adicional.

### CASO 20
El detector considera este caso de bajo riesgo debido a que el importe de la transacción es relativamente alto con 475.00 EUR, lo cual generalmente disminuye las probabilidades de fraude ya que los ladrones suelen probar tarjetas robadas con pequeños pagos antes de realizar cargos grandes. Sin embargo, hay un componente atípico en V4 (valor +3.313) que empuja hacia la posibilidad de fraude, aunque otros componentes como V11 y V14 presentan valores que contrarrestan este efecto negativo.

**Acción recomendada:** No requiere acción adicional.

### CASO 21
El detector considera sospechoso este caso debido a que el importe de la transacción es muy bajo, solo 1 EUR, lo cual puede ser un indicativo de prueba para tarjetas robadas. Además, aunque las variables V11 y V14 muestran valores que favorecen una clasificación legítima, la variable V4 tiene un valor muy alto (3.462) que empuja hacia el fraude, mientras que V1 también contribuye con un valor moderado pero aún favorable a lo legítimo (-1.756).

**Acción recomendada:** No requiere acción adicional.

### CASO 22
El detector considera sospechoso el caso 22 debido a que presenta un importe muy bajo de 1.00 EUR, lo cual es típico en intentos de prueba con tarjetas robadas antes de realizar cargos mayores. Además, las variables V12, V11, V4 y V14 muestran valores que empujan la transacción hacia ser considerada legítima, pero el importe tan pequeño sigue siendo un indicador significativo de posible fraude.

**Acción recomendada:** No requiere acción adicional.

### CASO 23
El detector considera este caso de baja probabilidad de fraude debido a que las variables V11, V14 y V10 presentan valores muy cercanos a lo normal (aportes negativos), lo cual sugiere comportamientos típicos. El importe de 183 EUR es mayor al importe medio del lote pero no se considera especialmente sospechoso en este contexto, ya que hay casos con importes similares o superiores que también tienen baja probabilidad de ser fraude.

**Acción recomendada:** No requiere acción adicional.

### CASO 24
El detector considera este caso de baja probabilidad de fraude debido a que las variables V4, V11 y V10 presentan valores que favorecen la clasificación como transacciones legítimas. Sin embargo, el importe de 7.15 EUR es relativamente bajo en comparación con el importe medio del lote, lo cual podría sugerir una posible prueba de tarjeta robada antes de un cargo mayor.

**Acción recomendada:** No requiere acción adicional.

### CASO 25
El detector considera este caso sospechoso debido a que la variable V4 presenta un valor muy alto (4.886), lo cual empuja hacia una mayor probabilidad de fraude, aunque variables como V11, V14 y V10 tienen valores que contrarrestan esta señal al presentarse en rangos considerados normales para transacciones legítimas. El importe de 304.49 EUR es significativamente superior al importe medio del lote (115.57 EUR), lo que también atrae la atención del sistema, aunque no alcanza niveles que sugieran un riesgo alto.

**Acción recomendada:** No requiere acción adicional.

### CASO 26
El detector considera este caso de bajo riesgo debido a que las variables V4, V12 y V21 presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar del importe pequeño de 7.70 EUR, estas características anómalas en los componentes PCA reducen la probabilidad de fraude a un nivel muy bajo.

**Acción recomendada:** No requiere acción adicional.

### CASO 27
El detector considera este caso de bajo riesgo debido a que las variables V4, V12, V7 y V21 presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar de ello, el importe de 34 EUR es relativamente pequeño en comparación con el importe medio del lote (115.57 EUR), lo cual podría sugerir una posible prueba de tarjeta robada antes de un cargo mayor.

**Acción recomendada:** No requiere acción adicional.

### CASO 28
El detector considera este caso de bajo riesgo debido a que las variables V4, V11, V19 y V21 presentan valores muy bajos, lo que contribuye significativamente a la clasificación como legítima. El importe de 3.70 EUR es pequeño, un monto típico para una transacción inicial cuando se prueba una tarjeta robada antes del cargo grande.

**Acción recomendada:** No requiere acción adicional.

### CASO 29
El detector considera este caso de bajo riesgo debido a que las variables V12, V4, V22 y V21 presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar del importe considerable de 436.59 EUR, estas variables atípicas reducen la probabilidad de fraude a un nivel muy bajo.

**Acción recomendada:** No requiere acción adicional.

### CASO 30
El detector considera este caso de bajo riesgo debido a que las variables V4, V10, V2 y V14 presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar de ello, el importe de 3.59 EUR es muy pequeño en comparación con el importe medio del lote (115.57 EUR), lo cual podría sugerir una prueba inicial típica de tarjetas robadas antes de realizar cargos más grandes.

**Acción recomendada:** No requiere acción adicional.

### CASO 31
El detector

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 94.82 | 16.7h | Sin veredicto | Revisar manualmente |
| 2 | 0.77 | 16.6h | Sin veredicto | Revisar manualmente |
| 3 | 349.51 | 16.6h | Sin veredicto | Revisar manualmente |
| 4 | 200.00 | 16.7h | Sin veredicto | Revisar manualmente |
| 5 | 800.00 | 16.7h | Sin veredicto | Revisar manualmente |
| 6 | 7.57 | 16.6h | Sin veredicto | Revisar manualmente |
| 7 | 310.00 | 16.7h | Sin veredicto | Revisar manualmente |
| 8 | 31.98 | 16.6h | Sin veredicto | Revisar manualmente |
| 9 | 29.60 | 16.6h | Sin veredicto | Revisar manualmente |
| 10 | 6.99 | 16.6h | Sin veredicto | Revisar manualmente |
| 11 | 1.56 | 16.7h | Sin veredicto | Revisar manualmente |
| 12 | 188.73 | 16.7h | Sin veredicto | Revisar manualmente |
| 13 | 28.92 | 16.7h | Sin veredicto | Revisar manualmente |
| 14 | 429.89 | 16.6h | Sin veredicto | Revisar manualmente |
| 15 | 264.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 16 | 1.98 | 16.7h | Sin veredicto | Revisar manualmente |
| 17 | 1035.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 18 | 144.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 19 | 258.90 | 16.6h | Sin veredicto | Revisar manualmente |
| 20 | 475.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 21 | 1.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 22 | 1.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 23 | 183.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 24 | 7.15 | 16.7h | Sin veredicto | Revisar manualmente |
| 25 | 304.49 | 16.6h | Sin veredicto | Revisar manualmente |
| 26 | 7.70 | 16.7h | Sin veredicto | Revisar manualmente |
| 27 | 34.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 28 | 3.70 | 16.6h | Sin veredicto | Revisar manualmente |
| 29 | 436.59 | 16.6h | Sin veredicto | Revisar manualmente |
| 30 | 3.59 | 16.6h | Sin veredicto | Revisar manualmente |
| 31 | 105.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 32 | 1.29 | 16.6h | Sin veredicto | Revisar manualmente |
| 33 | 3.12 | 16.7h | Sin veredicto | Revisar manualmente |
| 34 | 411.85 | 16.6h | Sin veredicto | Revisar manualmente |
| 35 | 39.99 | 16.6h | Sin veredicto | Revisar manualmente |
| 36 | 167.40 | 16.6h | Sin veredicto | Revisar manualmente |
| 37 | 0.42 | 16.7h | Sin veredicto | Revisar manualmente |
| 38 | 4290.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 39 | 5.51 | 16.6h | Sin veredicto | Revisar manualmente |
| 40 | 25.97 | 16.6h | Sin veredicto | Revisar manualmente |
| 41 | 69.32 | 16.7h | Sin veredicto | Revisar manualmente |
| 42 | 0.00 | 16.7h | Sin veredicto | Revisar manualmente |
| 43 | 50.42 | 16.7h | Sin veredicto | Revisar manualmente |
| 44 | 1363.21 | 16.7h | Sin veredicto | Revisar manualmente |
| 45 | 260.00 | 16.7h | Sin veredicto | Revisar manualmente |
| 46 | 2.67 | 16.7h | Sin veredicto | Revisar manualmente |
| 47 | 34.99 | 16.6h | Sin veredicto | Revisar manualmente |
| 48 | 98.04 | 16.6h | Sin veredicto | Revisar manualmente |
| 49 | 95.45 | 16.6h | Sin veredicto | Revisar manualmente |
| 50 | 184.95 | 16.6h | Sin veredicto | Revisar manualmente |
| 51 | 8.77 | 16.6h | Sin veredicto | Revisar manualmente |
| 52 | 1.00 | 16.6h | Sin veredicto | Revisar manualmente |
| 53 | 0.89 | 16.6h | Sin veredicto | Revisar manualmente |
| 54 | 102.95 | 16.6h | Sin veredicto | Revisar manualmente |
| 55 | 44.67 | 16.7h | Sin veredicto | Revisar manualmente |
| 56 | 2.00 | 16.7h | Sin veredicto | Revisar manualmente |
| 57 | 672.00 | 16.7h | Sin veredicto | Revisar manualmente |
| 58 | 103.41 | 16.6h | Sin veredicto | Revisar manualmente |
| 59 | 16.01 | 16.7h | Sin veredicto | Revisar manualmente |
| 60 | 7.82 | 16.6h | Sin veredicto | Revisar manualmente |

**60 casos en el expediente**: 0 confirmados, 0 descartados, 60 sin veredicto.
