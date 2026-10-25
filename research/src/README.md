# Research source code

Код загрузки и нормализации данных, расчёта согласованности, подготовки split, обучения моделей, агрегации и evaluation.

`data/create_review_group_folds_v1.py` создаёт новую версию пятичастных review-level folds по `item_group_id`. Текущий benchmark использует уже замороженный `review_group_folds_v1_1`: downstream-код читает сохранённые назначения и не запускает splitter повторно. Проверка замороженного артефакта:

```bash
python3 -m unittest research.tests.test_review_group_folds_v1
```

Генератор запускают только при явном создании следующей версии snapshot с новым именем артефакта; существующий `v1_1` не перезаписывают.

`data/build_binary_informativeness_target_v1.py` воспроизводимо строит замороженный производный target `high` против `not_high = low + medium`, не изменяя Gold Standard v1.1.

`evaluation/review_level_metrics.py` рассчитывает три независимых блока review-level оценки:

- F1, precision, recall и confusion matrix для `signal/no_signal`;
- Macro-F1 и поклассовые метрики направлений на строках с Gold-сигналом;
- четырёхклассовые метрики как вторичный общий результат.

CLI evaluator принимает Gold CSV и CSV прогнозов с одинаковым набором `review_id`. Предсказание `no_signal` на строке с Gold-сигналом учитывается как ошибка направления.

`models/run_review_level_benchmark_v1.py` воспроизводит B0–B2 на frozen folds. `models/run_frozen_transformer_benchmark_v1.py` сравнивает официальные checkpoints DeepPavlov в заранее зафиксированном режиме frozen CLS embeddings + Logistic Regression. `models/run_informativeness_benchmark_v1.py` оценивает бинарную служебную цель информативности.

`analysis/build_review_level_benchmark_report_v1.py` строит итоговый Markdown-отчёт и графики. Для headless-запуска рекомендуется задать writable cache, например `MPLCONFIGDIR=/tmp/ai_stylelink_matplotlib`.

`evaluation/run_yandex_external_audit_v1.py` проверяет SHA-256 замороженной B2 и один раз оценивает её на 300 строках Яндекс Маркета без настройки по внешним меткам.

`evaluation/run_item_level_pilot_v1.py` применяет замороженную B2 и бинарный informativeness-классификатор к полному WB snapshot, затем на одинаковых review-level predictions сравнивает equal-weight с `high=2 / not_high=1`. Скрипт сохраняет только exploratory agreement/disagreement, confidence и abstain, но не считает accuracy.
