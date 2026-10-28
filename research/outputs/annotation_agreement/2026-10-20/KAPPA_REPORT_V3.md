# Согласованность ручной разметки v3

Расчёт выполнен на одинаковых 1 200 `review_id`. Raw-файлы не изменялись.

## Основные результаты

| Поле | Scope | N | Agreement | Cohen’s Kappa | Тип |
|---|---|---:|---:|---:|---|
| fit_label | all | 1200 | 70.4% | 0.591 | unweighted |
| fit_signal | all | 1200 | 79.2% | 0.389 | unweighted |
| fit_label | both_annotators_signal | 824 | 87.1% | 0.799 | unweighted |
| signal_explicitness | all | 1200 | 62.6% | 0.432 | unweighted |
| user_action | all | 1198 | 40.9% | 0.210 | unweighted |
| internal_consistency | all | 1196 | 85.8% | 0.082 | unweighted |
| informativeness | all | 1197 | 54.1% | 0.291 | unweighted |
| informativeness | all | 1197 | 54.1% | 0.511 | quadratic_weighted |
| body_parameters | exact_set | 1198 | 77.5% | 0.576 | unweighted |
| fit_zones | exact_set | 1200 | 75.6% | 0.586 | unweighted |

## Обработка пропусков

- `fit_code` пересчитан детерминированно из `fit_label`.
- Пустая `signal_explicitness` восстановлена как `none` только для строк с `fit_label = no_signal`.
- Нейтральные значения `нет` и `не указана` преобразованы в пустые списки multi-label признаков.
- Полностью пустые слоты зон посадки преобразованы в пустой список: в первой книге пустота систематически используется вместо `не указана`.
- Остальные пропуски сохранены как `null`; Kappa для соответствующего поля рассчитан по полным парам.
- Порядок multi-label значений канонизирован; дубликаты удалены.

## Ограничение

Kappa измеряет согласованность разметчиков и не доказывает истинность меток. Multi-label поля дополнительно представлены бинарными Kappa по каждому значению в JSON-отчёте.
