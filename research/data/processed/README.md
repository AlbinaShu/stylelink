# Processed data

Версионированные датасеты для обучения, validation и финального test. Каждый набор должен иметь manifest с источниками, правилами фильтрации, split seed и списком `item_group_id` по split.

Единый указатель на текущую цепочку: [`CURRENT_SNAPSHOT.md`](CURRENT_SNAPSHOT.md).

`annotations/2026-10-24/` — текущий adjudication snapshot. Он содержит две нормализованные копии ручной разметки v3, попарную таблицу, очередь и 849 итоговых решений. Raw-книги не изменялись. Решения, включая исправление повторяющегося текста, подтверждены исследователем 24 октября 2026 года.

`adjudication_decisions_ai_v1.jsonl` и `adjudication_decisions_ai_v1_manifest.json` содержат AI-assisted решения и отдельную фиксацию их полного подтверждения исследователем. Статус snapshot — `human_confirmed_complete`.

`review_level/2026-10-24/` содержит канонический `review_level_dataset_v1_1` на 1 200 уникальных отзывов. Итоговые `fit_label`, `fit_code`, `signal_explicitness` и `informativeness` заполнены во всех строках: 849 строк взяты из adjudication, 351 — из совпавших ответов двух разметчиков.

`splits/2026-10-24/` содержит замороженные `review_group_folds_v1_1`, созданные `StratifiedGroupKFold` в scikit-learn 1.8.0 по `item_group_id`, target `fit_label`, `random_state=42`. В validation-folds попали 254, 238, 230, 241 и 237 отзывов. В раунде `k` fold `k` используется как validation, остальные четыре — как train. Downstream-код обязан читать сохранённый CSV, а не вызывать splitter заново.

`derived_targets/2026-10-24/` содержит замороженный `review_level_informativeness_binary_v1`: 270 `high` и 930 `not_high`, где `not_high = low + medium`. Это производная цель для явно версионированных экспериментов; исходное трёхуровневое поле Gold Standard не изменялось.

Дополнительные признаки (`body_parameters`, `fit_zones`, `user_action`, `internal_consistency`) перенесены только при согласии двух разметчиков. Расхождения сохранены в отдельных source-полях и `auxiliary_disagreements`, а не заменены предположительными значениями. Канонические правила для всех новых разметок зафиксированы в `docs/research/ANNOTATION_GUIDE_V4.md`, схема — в `research/config/review_annotation_schema_v4.json`.

`machine_annotations/2026-10-24/` содержит `wildberries_machine_annotations_v4_v1_1`, пересобранный на каноническом Gold v1.1 в scikit-learn 1.8.0. Все 40 474 исходные записи сохранены: 27 384 непустых текста имеют статус `predicted`, 13 090 пустых — `skipped_empty_text`.

Каталоги `annotations/2026-10-20/`, `review_level/2026-10-20/` и `machine_annotations/2026-10-20/` оставлены только для provenance и помечены `SUPERSEDED.md`. Их нельзя использовать в новых экспериментах или перезаписывать.
