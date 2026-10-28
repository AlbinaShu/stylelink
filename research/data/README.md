# Research data

Данные организуются по степени обработки:

- `raw/` — неизменённые выгрузки источников и ручной разметки;
- `interim/` — нормализованные таблицы, результаты валидации схемы и временные объединения;
- `processed/` — версионированные датасеты для обучения, validation и финальной оценки.

Каждая raw-выгрузка хранится в датированной папке с `manifest.json`. Файлы в `raw/` нельзя перезаписывать результатами очистки или adjudication.

Текущая двойная разметка: [`raw/annotations/2026-10-20/`](raw/annotations/2026-10-20/manifest.json).

Текущий snapshot Wildberries: [`raw/wildberries/2026-09-12/`](raw/wildberries/2026-09-12/manifest.json).

Текущий snapshot Яндекс Маркета: [`raw/yandex_market/2026-10-21/`](raw/yandex_market/2026-10-21/manifest.json). Он содержит 646 уникальных непустых отзывов по одежде из шести товарных карточек; персональные идентификаторы авторов не сохранялись.

Исторический вход машинной разметки v3: `interim/wildberries/2026-09-12/reviews_for_model_annotation_v3.jsonl`. Его схема сохранена в `../config/review_annotation_schema_v3.json`, а правила и контрольные суммы — в `interim/wildberries/2026-09-12/machine_annotation_manifest.json`. Текущая схема v4 кратко описана в [`SCHEMA.md`](SCHEMA.md).

Review-level Gold Standard `review_level_dataset_v1_1` на 1 200 отзывов: [`processed/review_level/2026-10-24/`](processed/review_level/2026-10-24/manifest.json).

Замороженные `review_group_folds_v1_1`: [`processed/splits/2026-10-24/`](processed/splits/2026-10-24/manifest.json). Все 1 200 отзывов и 40 `item_group_id` назначены ровно одному fold; пересечений товарных групп нет. Manifest фиксирует scikit-learn 1.8.0 и запрещает динамическую перегенерацию в benchmark.

Производная бинарная информативность: [`processed/derived_targets/2026-10-24/`](processed/derived_targets/2026-10-24/manifest.json). Target `review_level_informativeness_binary_v1` содержит 270 `high` и 930 `not_high = low + medium`; исходный Gold Standard v1.1 не изменён.

Итоговая машинная разметка v4 полного snapshot: [`processed/machine_annotations/2026-10-24/`](processed/machine_annotations/2026-10-24/manifest.json). В ней сохранены 27 384 predictions и 13 090 `skipped_empty_text`; это pseudo-labels, а не Gold Standard.

Аудит-набор Яндекс Маркета на 300 строк: [`processed/external_audit/2026-10-21/`](processed/external_audit/2026-10-21/manifest.json). CSV/XLSX для разметки не содержат model predictions, marketplace-сигналов, категории товара или страты отбора. Эти поля сохранены отдельно в `yandex_market_audit_300_source.jsonl` и не должны показываться разметчику до завершения работы.

Разметка в [Google Таблице](https://docs.google.com/spreadsheets/d/180uZg85rI86OHn5q4jdA8PzRBe8J8cvf-VnyT_Rl5zs/edit) завершена 23 октября 2026 года. Завершённый snapshot сохранён в `processed/external_audit/2026-10-21/completed/2026-10-23/`: исходный XLSX-экспорт, русская CSV-копия, нормализованные v4 CSV/JSONL, `validation_report.json`, manifest и SHA-256. Нормализованный датасет дополнен скрытыми до завершения разметки полями категории, товарной карточки и страты отбора.

Проверены 300 строк и 300 уникальных `review_id`. Для строк с меткой `нет сигнала` явность сигнала задана как обязательное `none`. Исходная таблица и нормализованный набор проходят схематическую проверку без автоматических исправлений и флагов нормализации.

Единое правило имён: человеко-ориентированные таблицы ручной разметки используют русские заголовки и русские значения справочников, совпадающие с двумя исходными файлами разметчиков. Технические файлы для кода и моделей (`JSONL`, schema/config, normalized/processed model datasets) сохраняют английские ключи `snake_case`; преобразование выполняется на границе импорта и экспорта.

В XLSX для ручной разметки `код метки` рассчитывается автоматически из `метки посадки`; вручную эту колонку заполнять не нужно. В CSV формулы не поддерживаются, поэтому код появляется после заполнения метки при последующем импорте и нормализации.
