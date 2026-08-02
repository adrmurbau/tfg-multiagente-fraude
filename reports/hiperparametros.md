# Búsqueda de hiperparámetros del detector

Búsqueda aleatoria sobre datos de entrenamiento, validada con validación cruzada. El conjunto de test permanece intacto hasta la comparación final.

| Split | AUC-PR referencia | AUC-PR ajustado | Δ | Veredicto |
|---|---|---|---|---|
| aleatorio | 0.8832 | 0.8801 | -0.0030 | La busqueda NO mejora en test: la configuracion inicial era tan buena o mejor. Posible sobreajuste a la validacion cruzada. |
| temporal | 0.7972 | 0.8007 | +0.0036 | La busqueda mejora marginalmente. La configuracion inicial ya estaba bien elegida. |

## Mejores hiperparámetros por split

### aleatorio

```json
{
  "subsample": 0.7,
  "scale_pos_weight": 24.0,
  "n_estimators": 800,
  "min_child_weight": 3,
  "max_depth": 6,
  "learning_rate": 0.05,
  "gamma": 0.5,
  "colsample_bytree": 0.9
}
```

### temporal

```json
{
  "subsample": 0.6,
  "scale_pos_weight": 23.4,
  "n_estimators": 800,
  "min_child_weight": 10,
  "max_depth": 3,
  "learning_rate": 0.05,
  "gamma": 0,
  "colsample_bytree": 0.6
}
```
