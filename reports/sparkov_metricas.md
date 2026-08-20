# Extension exploratoria: detector sobre dataset Sparkov

Dataset simulado con variables de negocio (comercio, categoria, distancia domicilio-comercio, edad), un ano de periodo, particion temporal con los ultimos dos meses como prueba.

| Modelo | Split | AUC-PR | ROC-AUC | Precision | Recall | F1 | P@100 |
|---|---|---|---|---|---|---|---|
| XGBoost-Sparkov | temporal | 0.0775 | 0.7227 | 0.0092 | 0.9485 | 0.0181 | 0.400 |
