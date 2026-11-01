# Review annotation schema v4

Каноническая машинно-проверяемая схема: [`../config/review_annotation_schema_v4.json`](../config/review_annotation_schema_v4.json). Правила разметки: [`../../docs/research/ANNOTATION_GUIDE_V4.md`](../../docs/research/ANNOTATION_GUIDE_V4.md).

## Основные поля

| Поле | Допустимые значения |
|---|---|
| `fit_label` | `runs_small`, `true_to_size`, `runs_large`, `no_signal` |
| `fit_code` | `-1`, `0`, `1` или `null` для `no_signal` |
| `signal_explicitness` | `explicit`, `implicit`, `none` |
| `informativeness` | `low`, `medium`, `high` |
| `body_parameters` | до трёх значений из схемы |
| `fit_zones` | до трёх значений из схемы |
| `user_action` | одно из действий, перечисленных в схеме |
| `internal_consistency` | `consistent`, `contradictory`, `unclear` |

В machine-annotation файле прогнозы находятся в объекте `prediction`; вероятности, версия модели, время прогноза, статус и ошибка сохраняются отдельно для provenance. `source_signals` не являются Gold Standard.

Основная B2 использует только текст. Дополнительные ручные поля нужны для анализа и явно названных ablation, но не должны незаметно попадать в production-вход.
