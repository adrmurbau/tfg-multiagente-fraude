# Informe de ventana 6

- Transacciones: 1375
- Casos: 2

CASO 11

El detector considera este caso sospechoso debido a que la transacción tiene un importe muy bajo, específicamente 2.69 EUR, lo cual puede indicar una prueba de tarjeta robada antes de realizar cargos mayores. Además, las variables V14 (-0.758), V12 (0.303) y V21 (-0.559) muestran valores atípicamente bajos o altos que contribuyen significativamente a elevar el riesgo hacia fraude. Aunque la variable V15 también tiene un efecto negativo aunque menos pronunciado, estas características anómalas en los componentes PCA hacen que sea poco probable una transacción legítima y aumentan las alertas sobre este caso.

CASO 12

El detector considera este caso de bajo riesgo debido a que el importe es relativamente pequeño (17.33 EUR) y varias variables anónimas, como V14 (-0.659), V12 (0.807) y V21 (0.303), presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar del importe bajo, estas características anómalas en las variables PCA indican un comportamiento normal sin señales alarmantes.

CASO 13

El detector considera sospechoso este caso debido a que el valor atípico de la variable V14 (+1.367) empuja hacia un mayor riesgo de fraude, aunque variables como V12 (-2.110), V1 (-1.913) y V4 (-1.673) contrarrestan este efecto, manteniendo el nivel de riesgo en general bajo. El importe de 246.46 EUR es significativamente mayor que el importe medio del lote (82.43 EUR), lo cual también atrae cierta atención.

CASO 14

El detector considera este caso de bajo riesgo debido a que las variables V14 (-0.759), V11 (-0.667) y V7 (-0.682) presentan valores que tienden a indicar una transacción legítima, aunque el importe de 134.99 EUR es algo superior al importe medio del lote (82.43 EUR), lo cual podría generar cierta alerta si no se acompañara con otros factores que indiquen fraude.

CASO 15

El detector considera que la transacción de 76.33 EUR es ligeramente sospechosa debido a un valor atípico en V14 (-0.829), lo cual empuja hacia una mayor probabilidad de fraude. Sin embargo, otros factores como el importe moderado y los valores normales en las variables V12 (0.375) y V4 (-0.673) ayudan a disminuir esta posibilidad, manteniendo así un nivel de riesgo bajo para este caso.

CASO 16

El detector considera sospechoso el caso debido a que la variable V4 presenta un valor muy alto (4.463), lo cual empuja hacia una mayor probabilidad de fraude, aunque variables como V14 (-0.759), V11 (-0.829) y V10 (-0.682) tienen valores que contrarrestan esta señal al presentar valores bajos y contribuir hacia una transacción legítima. A pesar de esto, el importe de 152.34 EUR es significativamente mayor que el importe medio del lote (82.43 EUR), lo que añade cierta incertidumbre al caso.

CASO 17

El detector considera que la transacción de 17.50 EUR es ligeramente sospechosa debido a un valor muy atípico en V14 (-0.829), lo cual empuja hacia una mayor probabilidad de fraude. Sin embargo, otros componentes como V1 (0.375) y V12 (0.682) muestran valores que favorecen la autenticidad de la transacción, manteniendo el riesgo general en nivel bajo.

CASO 18

El detector considera que la transacción es ligeramente sospechosa debido a un valor muy atípico en el componente V4 (3.00), lo cual empuja hacia una mayor probabilidad de fraude. Sin embargo, otros componentes como V10 (-2.68) y V2 (0.59) contrarrestan este efecto al señalar características que suelen ser normales. A pesar de esto, la transacción es muy pequeña con solo 3 euros, un monto típico para pruebas fraudulentas antes de realizar cargos mayores.

CASO 19

El detector considera este caso de bajo riesgo debido a que el importe es relativamente pequeño (49.90 EUR) y las variables V4 (-2.68), V16 (-2.57) y V3 (-2.55) presentan valores que contribuyen a disminuir la probabilidad de fraude. Sin embargo, el modelo aún identifica ciertos patrones en los componentes anonimizados que hacen que este caso no sea completamente seguro, aunque la probabilidad de fraude es muy baja.

CASO 20

El detector considera este caso sospechoso debido a que el importe de la transacción, 294.07 EUR, es significativamente mayor al importe medio del lote (82.43 EUR). Además, las variables V1 (-2.62), V12 (-2.53), V10 (-2.05) y V14 (-2.03) presentan valores que contribuyen negativamente a la probabilidad de fraude, lo que sugiere características atípicas en los componentes anonimizados del caso.

CASO 21

El detector considera este caso sospechoso debido a que varias variables, como V4 (-2.68), V11 (-2.57) y V21 (0.37), presentan valores muy bajos que empujan la transacción hacia lo legítimo. A pesar de esto, el importe de 143.80 EUR es significativamente mayor al importe medio del lote (82.43 EUR), lo cual podría sugerir cierto nivel de riesgo aunque sea bajo.

CASO 22

El detector considera este caso de bajo riesgo debido a que el importe de la transacción es relativamente alto (91.74 EUR) y presenta valores en las variables V11 (-2.68), V4 (-2.57) y V21 (0.37) que contribuyen negativamente al indicio de fraude, sugiriendo comportamientos más típicos o legítimos.

CASO 23

El detector considera este caso sospechoso debido a que el importe de la transacción, 145.82 EUR, es significativamente mayor al importe medio del lote (82.43 EUR). Además, las variables V1 (-2.68), V12 (-2.57) y V4 (-2.05) presentan valores que contribuyen hacia una clasificación menos sospechosa, pero el conjunto de características en general sigue siendo lo suficientemente atípico como para generar una probabilidad de fraude baja.

CASO 24

El detector considera este caso sospechoso debido a que el importe de la transacción es bajo, con solo 7.36 EUR, lo cual puede ser un indicativo de una tarjeta robada probando su funcionalidad antes de realizar cargos mayores. Además, las variables V11 (-2.68), V7 (0.59) y V5 (-2.57) muestran valores que contribuyen a considerar la transacción legítima, pero el modelo detecta patrones atípicos en estas componentes que sugieren cierto grado de riesgo, aunque este sea bajo.

CASO 25

El detector considera este caso de bajo riesgo debido a que el importe es relativamente pequeño (44.96 EUR) y las variables V11 (-2.68), V25 (-2.57) y V12 (-2.05) presentan valores que contribuyen hacia la clasificación como transacción legítima. Sin embargo, aunque estos factores reducen la probabilidad de fraude, el caso aún se mantiene en un nivel de riesgo bajo debido a otros componentes no mencionados que podrían estar influyendo en la evaluación general del sistema.

CASO 26

El detector considera este caso de bajo riesgo debido a que el importe es relativamente pequeño (12.11 EUR) y las variables V11 (-2.68), V4 (-2.57) y V14 (-2.05) presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. Sin embargo, aunque estos factores reducen la probabilidad de fraude, el caso aún se mantiene en un nivel de riesgo bajo debido a otros aspectos no mencionados que podrían estar influyendo en la evaluación general del sistema.

CASO 27

El detector considera que el caso es de bajo riesgo debido a varios factores, entre ellos un importe pequeño de 5.95 EUR y valores en las variables V4 (-2.68), V11 (-2.57) y V12 (-2.05) que contribuyen negativamente al indicador de fraude. Aunque la hora del día (17:50) no se menciona específicamente como factor relevante, el conjunto de características observadas sugiere una transacción poco probable de ser fraudulenta según los patrones analizados por el modelo.

CASO 28

El detector considera este caso de bajo riesgo debido a que las variables V14 (-2.68), V12 (-2.57) y V28 (0.37) presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. Sin embargo, el importe de 498 EUR es considerablemente mayor al importe medio del lote (82.43 EUR), lo que podría sugerir cierta atención adicional aunque no indica necesariamente fraude.

CASO 29

El detector considera que el caso tiene un riesgo bajo de fraude debido a varios factores, entre ellos el importe transaccionado de 75.52 EUR, que es similar al promedio del lote y no se corresponde con los patrones típicamente asociados a intentos fraudulentos. Además, las variables V1 (-2.68), V10 (0.37) y V22 (-2.57) presentan valores que contribuyen negativamente hacia la clasificación de transacciones legítimas, lo que ayuda a disminuir aún más el riesgo percibido en este caso.

CASO 30

El detector considera este caso de bajo riesgo debido a que las variables V4 (-2.68), V14 (-2.57) y V11 (-2.05) presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar del importe considerable de 475 EUR, estas variables anónimas tienen un efecto negativo en la probabilidad de fraude, lo que reduce las señales sospechosas.

CASO 31

El detector considera este caso sospechoso debido a que una variable anónima (V4) presenta un valor alto, lo cual empuja la transacción hacia el fraude. Sin embargo, otras variables como V11 (-2.68) y V14 (-2.57) muestran valores bajos que disminuyen las posibilidades de ser fraudulenta. Además, el importe de 11.34 EUR es muy bajo en comparación con el importe medio del lote (82.43 EUR), lo cual también reduce la probabilidad de fraude ya que los ladrones suelen probar tarjetas robadas con pequeños pagos antes de realizar cargos mayores.

CASO 32

El detector considera que la transacción de 49.95 EUR es ligeramente sospechosa debido a un valor atípico en el componente V4 (-2.68), lo cual empuja hacia una mayor probabilidad de fraude. Sin embargo, otros componentes como V14 (-2.57) y V10 (0.37) presentan valores que disminuyen la posibilidad de fraude, manteniendo así el riesgo general en nivel bajo.

CASO 33

El detector considera este caso de bajo riesgo debido a que el importe de la transacción es moderado (86.00 EUR) y se encuentra dentro del rango normal para las transacciones analizadas, además de que los valores en las variables V12 (-2.57), V16 (-2.05) y V4 (-2.68) son consistentes con comportamientos legítimos, lo que contribuye a minimizar la probabilidad de fraude.

CASO 34

El detector considera este caso de bajo riesgo debido a que las variables V1 (-2.68), V12 (-2.57) y V4 (-2.05) muestran valores que tienden a ser comunes en transacciones legítimas, mientras que el valor atípico en la variable V14 (0.37) también favorece esta clasificación. A pesar del importe de 212.36 EUR, que es mayor que el importe medio del lote, las características anómalas de otras variables no son lo suficientemente preocupantes para elevar significativamente la probabilidad de fraude.

CASO 35

El detector considera este caso de bajo riesgo debido a que los valores de las variables V4 (-2.68), V12 (-2.57), V14 (0.37) y V10 (-2.05) son muy bajos o negativos, lo cual empuja la transacción hacia ser legítima. A pesar del importe pequeño (1.29 EUR), estas características anómalas en las variables PCA no generan suficiente indicio de fraude para elevar el riesgo a un nivel más alto.

CASO 36

El detector considera que el caso es ligeramente sospechoso debido a un valor muy atípico en la variable V14 (-2.57), lo cual empuja hacia una mayor probabilidad de fraude. Sin embargo, otros componentes como V1 (0.37) y V12 (-2.68) contrarrestan este efecto al indicar comportamientos más normales. El importe de 12.31 EUR es bajo, un monto que a menudo se utiliza para probar tarjetas robadas antes de realizar cargos mayores.

CASO 37

El detector considera este caso de bajo riesgo debido a que las variables V14 (-2.68), V12 (-2.57), V11 (0.37) y V28 (-2.05) presentan valores que contribuyen significativamente a clasificar la transacción como legítima. A pesar del importe elevado de 1618.42 EUR, estos componentes anónimos muestran patrones típicos de actividad no fraudulenta, lo que disminuye las probabilidades de fraude.

CASO 38

El detector considera este caso de bajo riesgo debido a que las variables V12 (-2.68), V1 (0.37), V4 (-2.57) y V21 (-2.05) presentan valores que contribuyen significativamente hacia la clasificación como transacción legítima. A pesar del importe considerable de 247.04 EUR, estas variables anómalas tienen un efecto negativo en la probabilidad de fraude, manteniendo el riesgo bajo.

CASO 39

El detector considera este caso de bajo riesgo debido a que el importe es relativamente pequeño, con solo 15 euros, lo cual no se corresponde típicamente con transacciones fraudulentas grandes y peligrosas. Además, las variables V4 (-2.68), V27 (0.37) y V24 (-2.05) presentan valores que contribuyen a considerar la transacción legítima, ya que sus efectos son negativos y ayudan a disminuir la probabilidad de fraude.

CASO 40

El detector considera este caso de bajo riesgo debido a que las variables V14 (-2.68), V11 (0.37) y V4 (-2.57) presentan valores que tienden a señalar una transacción legítima, con un importe de 142.15 EUR que no es especialmente pequeño ni inusual para el lote analizado. Sin embargo, la probabilidad de fraude sigue siendo muy baja pero no nula, lo que indica que aunque hay factores que favorecen una transacción legítima, aún existen ciertos elementos que podrían merecer una revisión adicional.

CASO 41

El detector considera este caso sospechoso debido a que el importe de 400 EUR es significativamente mayor al importe medio del lote, y aunque las variables V10 (-2.68), V1 (0.37), V4 (-2.57) y V26 (-2.05) presentan valores que empujan la transacción hacia lo legítimo, su probabilidad de fraude sigue siendo muy baja.

CASO 42

El detector considera este caso sospechoso debido a que el importe de la transacción es bajo, con solo 7.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 0.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 2 | 1.00 | 17.5h | Sin veredicto | Revisar manualmente |
| 3 | 1059.28 | 17.4h | Sin veredicto | Revisar manualmente |
| 4 | 29.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 5 | 355.10 | 17.5h | Sin veredicto | Revisar manualmente |
| 6 | 331.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 7 | 60.69 | 17.5h | Sin veredicto | Revisar manualmente |
| 8 | 106.04 | 17.4h | Sin veredicto | Revisar manualmente |
| 9 | 60.69 | 17.5h | Sin veredicto | Revisar manualmente |
| 10 | 149.31 | 17.5h | Sin veredicto | Revisar manualmente |
| 11 | 2.69 | 17.4h | Sin veredicto | Revisar manualmente |
| 12 | 17.33 | 17.4h | Sin veredicto | Revisar manualmente |
| 13 | 246.46 | 17.4h | Sin veredicto | Revisar manualmente |
| 14 | 134.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 15 | 76.33 | 17.4h | Sin veredicto | Revisar manualmente |
| 16 | 152.34 | 17.5h | Sin veredicto | Revisar manualmente |
| 17 | 17.50 | 17.4h | Sin veredicto | Revisar manualmente |
| 18 | 3.00 | 17.5h | Sin veredicto | Revisar manualmente |
| 19 | 49.90 | 17.3h | Sin veredicto | Revisar manualmente |
| 20 | 294.07 | 17.5h | Sin veredicto | Revisar manualmente |
| 21 | 143.80 | 17.5h | Sin veredicto | Revisar manualmente |
| 22 | 91.74 | 17.4h | Sin veredicto | Revisar manualmente |
| 23 | 145.82 | 17.4h | Sin veredicto | Revisar manualmente |
| 24 | 7.36 | 17.5h | Sin veredicto | Revisar manualmente |
| 25 | 44.96 | 17.4h | Sin veredicto | Revisar manualmente |
| 26 | 12.11 | 17.5h | Sin veredicto | Revisar manualmente |
| 27 | 5.95 | 17.5h | Sin veredicto | Revisar manualmente |
| 28 | 498.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 29 | 75.52 | 17.5h | Sin veredicto | Revisar manualmente |
| 30 | 475.00 | 17.5h | Sin veredicto | Revisar manualmente |
| 31 | 11.34 | 17.5h | Sin veredicto | Revisar manualmente |
| 32 | 49.95 | 17.4h | Sin veredicto | Revisar manualmente |
| 33 | 86.00 | 17.5h | Sin veredicto | Revisar manualmente |
| 34 | 212.36 | 17.4h | Sin veredicto | Revisar manualmente |
| 35 | 1.29 | 17.4h | Sin veredicto | Revisar manualmente |
| 36 | 12.31 | 17.4h | Sin veredicto | Revisar manualmente |
| 37 | 1618.42 | 17.4h | Sin veredicto | Revisar manualmente |
| 38 | 247.04 | 17.4h | Sin veredicto | Revisar manualmente |
| 39 | 15.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 40 | 142.15 | 17.4h | Sin veredicto | Revisar manualmente |
| 41 | 400.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 42 | 7.40 | 17.5h | Sin veredicto | Revisar manualmente |
| 43 | 119.00 | 17.5h | Sin veredicto | Revisar manualmente |
| 44 | 10.00 | 17.3h | Sin veredicto | Revisar manualmente |
| 45 | 596.30 | 17.5h | Sin veredicto | Revisar manualmente |
| 46 | 140.99 | 17.4h | Sin veredicto | Revisar manualmente |
| 47 | 6.99 | 17.5h | Sin veredicto | Revisar manualmente |
| 48 | 1299.23 | 17.4h | Sin veredicto | Revisar manualmente |
| 49 | 10.22 | 17.5h | Sin veredicto | Revisar manualmente |
| 50 | 20.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 51 | 4.49 | 17.4h | Sin veredicto | Revisar manualmente |
| 52 | 45.89 | 17.4h | Sin veredicto | Revisar manualmente |
| 53 | 5.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 54 | 11.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 55 | 298.00 | 17.4h | Sin veredicto | Revisar manualmente |
| 56 | 1.98 | 17.4h | Sin veredicto | Revisar manualmente |
| 57 | 6.29 | 17.4h | Sin veredicto | Revisar manualmente |
| 58 | 4.45 | 17.5h | Sin veredicto | Revisar manualmente |
| 59 | 20.10 | 17.5h | Sin veredicto | Revisar manualmente |
| 60 | 157.81 | 17.5h | Sin veredicto | Revisar manualmente |

**60 casos en el expediente**: 0 confirmados, 0 descartados, 60 sin veredicto.
