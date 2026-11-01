# Данные исследования

Канонические локальные данные находятся в [`../../../research/data/`](../../../research/data/README.md). Этот каталог документации не содержит отдельной копии datasets.

## Основные версии

- Raw-разметка двух экспертов: `research/data/raw/annotations/2026-10-20/`.
- Gold Standard `review_level_dataset_v1_1`: `research/data/processed/review_level/2026-10-24/`.
- Frozen folds `review_group_folds_v1_1`: `research/data/processed/splits/2026-10-24/`.
- Yandex external audit: `research/data/processed/external_audit/2026-10-21/`.
- Machine pseudo-labels: `research/data/processed/machine_annotations/2026-10-24/`.

Для каждой версии используются manifest и SHA-256. Raw и замороженные processed-артефакты не перезаписываются; исправление создаётся как новая версия.

Схема, состав и ограничения описаны в [DATASET_GUIDE.md](../DATASET_GUIDE.md). Точные поля файлов и команды проверки — в [`../../../research/data/README.md`](../../../research/data/README.md).
