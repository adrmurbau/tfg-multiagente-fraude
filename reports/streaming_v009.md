# Informe de ventana 9

- Transacciones: 1381
- Casos: 2

CASO 31

El detector considera sospechoso este caso debido principalmente al importe y ciertos valores atípicos en las variables PCA. La transacción tiene un importe de 379.29 EUR, que es significativamente mayor a la media del lote (92.85 EUR). Aunque generalmente los montos más altos no son automáticamente indicativos de fraude, este caso presenta valores atípicos en las variables V4 y V10.

La variable V4 tiene un valor muy alto, lo que empuja hacia una mayor probabilidad de fraude. Esto sugiere comportamientos poco comunes o inusuales asociados con esta transacción. Además, el valor atípico en la variable V10 también contribuye a señalar la transacción como sospechosa.

Sin embargo, otros componentes PCA presentan valores que contrarrestan parcialmente este efecto. Las variables V14 y V11 muestran valores bajos que empujan hacia una clasificación legítima, lo cual ayuda a mantener el riesgo en un nivel bajo. Sin embargo, la combinación de estos factores atípicos junto con el importe elevado lleva al detector a considerar este caso como sospechoso.

En resumen, aunque hay indicadores que apuntan hacia una transacción legítima, los valores anómalos en las variables V4 y V10, junto con el importe significativamente mayor a la media del lote, hacen que el detector vea cierta inconsistencia en esta transacción y por lo tanto la clasifique como sospechosa.

---

| Caso | Importe (EUR) | Hora | Veredicto | Accion recomendada |
|---|---|---|---|---|
| 1 | 10.70 | 18.0h | Sin veredicto | Revisar manualmente |
| 2 | 9.29 | 17.9h | Sin veredicto | Revisar manualmente |
| 3 | 4.49 | 17.9h | Sin veredicto | Revisar manualmente |
| 4 | 101.36 | 17.9h | Sin veredicto | Revisar manualmente |
| 5 | 17.90 | 18.0h | Sin veredicto | Revisar manualmente |
| 6 | 149.00 | 17.9h | Sin veredicto | Revisar manualmente |
| 7 | 2500.00 | 17.9h | Sin veredicto | Revisar manualmente |
| 8 | 4.54 | 18.0h | Sin veredicto | Revisar manualmente |
| 9 | 494.00 | 18.0h | Sin veredicto | Revisar manualmente |
| 10 | 37.93 | 17.9h | Sin veredicto | Revisar manualmente |
| 11 | 176.98 | 17.9h | Sin veredicto | Revisar manualmente |
| 12 | 104.86 | 17.9h | Sin veredicto | Revisar manualmente |
| 13 | 318.00 | 17.9h | Sin veredicto | Revisar manualmente |
| 14 | 182.50 | 17.9h | Sin veredicto | Revisar manualmente |
| 15 | 15.00 | 17.8h | Sin veredicto | Revisar manualmente |
| 16 | 70.84 | 17.9h | Sin veredicto | Revisar manualmente |
| 17 | 126.72 | 17.9h | Sin veredicto | Revisar manualmente |
| 18 | 248.84 | 18.0h | Sin veredicto | Revisar manualmente |
| 19 | 432.95 | 17.9h | Sin veredicto | Revisar manualmente |
| 20 | 11.50 | 18.0h | Sin veredicto | Revisar manualmente |
| 21 | 18.96 | 17.9h | Sin veredicto | Revisar manualmente |
| 22 | 3995.94 | 18.0h | Sin veredicto | Revisar manualmente |
| 23 | 258.67 | 17.9h | Sin veredicto | Revisar manualmente |
| 24 | 8.99 | 18.0h | Sin veredicto | Revisar manualmente |
| 25 | 1.40 | 17.9h | Sin veredicto | Revisar manualmente |
| 26 | 23.80 | 17.9h | Sin veredicto | Revisar manualmente |
| 27 | 1.98 | 17.9h | Sin veredicto | Revisar manualmente |
| 28 | 8.99 | 17.9h | Sin veredicto | Revisar manualmente |
| 29 | 3.99 | 17.9h | Sin veredicto | Revisar manualmente |
| 30 | 459.24 | 17.9h | Sin veredicto | Revisar manualmente |
| 31 | 379.29 | 17.8h | Sin veredicto | Revisar manualmente |
| 32 | 5.95 | 18.0h | Sin veredicto | Revisar manualmente |
| 33 | 1.00 | 17.9h | Sin veredicto | Revisar manualmente |
| 34 | 200.00 | 18.0h | Sin veredicto | Revisar manualmente |
| 35 | 15.00 | 18.0h | Sin veredicto | Revisar manualmente |
| 36 | 12.14 | 17.9h | Sin veredicto | Revisar manualmente |
| 37 | 2494.40 | 17.9h | Sin veredicto | Revisar manualmente |
| 38 | 1.00 | 17.9h | Sin veredicto | Revisar manualmente |
| 39 | 23.74 | 17.9h | Sin veredicto | Revisar manualmente |
| 40 | 89.40 | 18.0h | Sin veredicto | Revisar manualmente |
| 41 | 53.00 | 18.0h | Sin veredicto | Revisar manualmente |
| 42 | 43.00 | 18.0h | Sin veredicto | Revisar manualmente |
| 43 | 5.90 | 18.0h | Sin veredicto | Revisar manualmente |
| 44 | 550.00 | 17.9h | Sin veredicto | Revisar manualmente |
| 45 | 175.40 | 17.9h | Sin veredicto | Revisar manualmente |
| 46 | 697.50 | 18.0h | Sin veredicto | Revisar manualmente |
| 47 | 24.15 | 17.9h | Sin veredicto | Revisar manualmente |
| 48 | 2.69 | 18.0h | Sin veredicto | Revisar manualmente |
| 49 | 237.00 | 18.0h | Sin veredicto | Revisar manualmente |
| 50 | 37.93 | 17.9h | Sin veredicto | Revisar manualmente |
| 51 | 514.90 | 17.9h | Sin veredicto | Revisar manualmente |
| 52 | 450.00 | 18.0h | Sin veredicto | Revisar manualmente |
| 53 | 336.82 | 18.0h | Sin veredicto | Revisar manualmente |
| 54 | 29.10 | 17.9h | Sin veredicto | Revisar manualmente |
| 55 | 3.89 | 18.0h | Sin veredicto | Revisar manualmente |
| 56 | 127.69 | 18.0h | Sin veredicto | Revisar manualmente |
| 57 | 546.00 | 17.8h | Sin veredicto | Revisar manualmente |
| 58 | 418.24 | 17.9h | Sin veredicto | Revisar manualmente |
| 59 | 99.00 | 17.9h | Sin veredicto | Revisar manualmente |
| 60 | 1.00 | 18.0h | Sin veredicto | Revisar manualmente |

**60 casos en el expediente**: 0 confirmados, 0 descartados, 60 sin veredicto.
