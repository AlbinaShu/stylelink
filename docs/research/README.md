# Исследование ML-рекомендации размера

Актуальное состояние зафиксировано на 24 октября 2026 года. Исследование отделено от локального продуктового прототипа: выбранная модель B2 пока не подключена к сайту.

## Что завершено

- Собран Gold Standard `review_level_dataset_v1_1`: 1 200 отзывов из 40 товарных групп.
- Заморожены пять сбалансированных folds по `item_group_id`; одна товарная группа не попадает одновременно в train и validation.
- В едином протоколе сравнены B0, B1, B2, frozen ruBERT и frozen DistilRuBERT.
- Выбрана B2: TF-IDF + Logistic Regression. Заморожен порог `confidence/abstain = 0.60`.
- После выбора модель один раз проверена на 300 размеченных отзывах Яндекс Маркета.
- Проведён exploratory item-level pilot equal-weight против informativeness-weighted на 40 товарах.

## Основные результаты

| Проверка | Signal F1 | Direction Macro-F1 | 4-class Macro-F1 | Accuracy |
|---|---:|---:|---:|---:|
| WB, 5-fold OOF, B2 | 0.822 | 0.754 | 0.702 | 0.694 |
| Яндекс Маркет, 300 отзывов | 0.837 | 0.756 | 0.746 | 0.830 |

При пороге `0.60` на WB coverage равен `0.530`, а accuracy на принятых прогнозах — `0.835`. На Яндекс Маркете coverage равен `0.507`.

В item-level pilot методы совпали для 37 из 40 товаров. Weighted aggregation изменила три решения, но победитель не выбран: независимого item-level Gold Standard пока нет.

## Что результаты не доказывают

- Transformer-модели не дообучались end-to-end: сравнивались frozen CLS-признаки с Logistic Regression.
- Яндекс-набор размечен одним исследователем и включает только шесть карточек; это проверка переноса, а не репрезентативная оценка всего маркетплейса.
- Informativeness — производная служебная метка; её использование в весах пока является гипотезой.
- Персональная рекомендация S/M/L не проверялась: для неё нужны параметры пользователя и размерная сетка.

## Навигация

- [RESEARCH_STATUS.md](RESEARCH_STATUS.md) — статус, выводы и следующий этап.
- [DATASET_GUIDE.md](DATASET_GUIDE.md) — версии данных и правила использования.
- [MODEL_NOTES.md](MODEL_NOTES.md) — модели, метрики и интерпретация.
- [ML_REQUIREMENTS.md](ML_REQUIREMENTS.md) — контракт исследовательского и продуктового ML.
- [METHODOLOGICAL_DECISIONS.md](METHODOLOGICAL_DECISIONS.md) — принятые методологические решения.
- [ADJUDICATION_METHOD_V1.md](ADJUDICATION_METHOD_V1.md) — происхождение итоговых review-level меток.
- [`../../research/README.md`](../../research/README.md) — структура артефактов и команды воспроизведения.

Подробные численные отчёты являются источником истины: [`../../research/outputs/benchmarks/review_level/2026-10-24/`](../../research/outputs/benchmarks/review_level/2026-10-24/), [`../../research/outputs/external_audit/2026-10-24/`](../../research/outputs/external_audit/2026-10-24/) и [`../../research/outputs/item_level_pilot/2026-10-24/`](../../research/outputs/item_level_pilot/2026-10-24/).
