# Metricas del detector — Fase 2

AUC-PR es la metrica principal: con una prevalencia del 0,173 %, su linea base es 0,0017.

| Modelo | Split | AUC-PR | ROC-AUC | Precision | Recall | F1 | P@100 |
|---|---|---|---|---|---|---|---|
| XGBoost | aleatorio | 0.8832 | 0.9810 | 0.8723 | 0.8367 | 0.8542 | 0.830 |
| RandomForest | aleatorio | 0.8627 | 0.9701 | 0.9186 | 0.8061 | 0.8587 | 0.830 |
| IsolationForest | aleatorio | 0.1520 | 0.9514 | 0.2525 | 0.2551 | 0.2538 | 0.250 |
| XGBoost | temporal | 0.7972 | 0.9849 | 0.8769 | 0.7600 | 0.8143 | 0.600 |
| RandomForest | temporal | 0.8200 | 0.9654 | 0.9821 | 0.7333 | 0.8397 | 0.610 |
| IsolationForest | temporal | 0.0340 | 0.9425 | 0.0095 | 0.0133 | 0.0111 | 0.000 |

## Los tres modelos

| Modelo | Aprendizaje | Construccion | Que busca |
|---|---|---|---|
| XGBoost | Supervisado | Boosting: arboles en secuencia, cada uno corrige al anterior | La frontera entre clases |
| Random Forest | Supervisado | Bagging: arboles en paralelo, voto promediado | La frontera entre clases |
| Isolation Forest | No supervisado | Cortes aleatorios; mide cuanto cuesta aislar cada punto | Lo infrecuente |

Los dos primeros usan las etiquetas; el tercero no las ve nunca. De ahi que el Isolation Forest rinda mal en AUC-PR: responde a otra pregunta. Raro no es lo mismo que fraudulento, y en este dataset la mayor parte de lo atipico es legitimo.

XGBoost es ademas el unico que expone `pred_contribs`, que calcula valores SHAP exactos sin aproximacion post-hoc. Es lo que alimenta las explicaciones de la capa de agentes, de modo que la eleccion no depende solo de la metrica.
