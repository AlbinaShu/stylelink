# Current research snapshot

Текущая каноническая цепочка review-level исследования заморожена датой `2026-10-24` и версией `v1_1`:

1. Подтверждённые adjudication-решения: `annotations/2026-10-24/adjudication_decisions_ai_v1.jsonl`.
2. Gold Standard: `review_level/2026-10-24/review_level_dataset_v1_1.csv`.
3. Замороженные folds: `splits/2026-10-24/review_group_folds_v1_1.csv`.
4. Производная бинарная информативность: `derived_targets/2026-10-24/review_level_informativeness_binary_v1.csv`.
5. Машинная разметка: `machine_annotations/2026-10-24/reviews_machine_annotated_v4_v1_1.jsonl`.
6. Диагностическая EDA: `research/outputs/eda/2026-10-24/`.
7. Диагностические модели разметки: `research/outputs/models/review_annotation_v4/2026-10-24/`.
8. Frozen review-level модель и порог: `research/config/frozen_review_model_v1.json`.
9. Внешний аудит Яндекс Маркета: `research/outputs/external_audit/2026-10-24/`.
10. Exploratory item-level pilot: `research/outputs/item_level_pilot/2026-10-24/`.

Все новые review-level benchmark-эксперименты должны ссылаться только на эту цепочку и на сохранённые fold assignments.

Каталоги предыдущих дат и файлы folds `v1` считаются superseded. Они остаются в репозитории для provenance, но не используются, не редактируются и не перезаписываются. Если найдётся проверенная резервная копия состояния до исправления, её можно восстановить только в отдельный legacy snapshot после сверки с историческими SHA-256; текущую цепочку `2026-10-24` это не меняет.
