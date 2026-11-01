# Research workspace

Этот каталог содержит локальные артефакты ML-исследования AI StyleLink. Методология, требования и актуальный план находятся в [`../docs/research/`](../docs/research/README.md).

Проверенный статус на 24 октября 2026 года, полученные метрики, ограничения и следующий порядок работ собраны в [`../docs/research/RESEARCH_STATUS.md`](../docs/research/RESEARCH_STATUS.md).

## Структура

```text
research/
├── data/
│   ├── raw/            неизменённые выгрузки и snapshots источников
│   ├── interim/        промежуточные нормализованные данные
│   └── processed/      зафиксированные наборы для обучения и оценки
├── notebooks/          воспроизводимый исследовательский анализ
├── src/                код подготовки данных, обучения и evaluation
└── outputs/            метрики, таблицы, графики и отчёты экспериментов
```

В репозиторий перенесены новые raw-файлы двойной разметки, полный snapshot Wildberries на 40 474 отзыва, производные агрегаты и скрипты сбора. Актуальный EDA находится в [`notebooks/01_review_fit_eda.ipynb`](notebooks/01_review_fit_eda.ipynb) и [`outputs/eda/2026-10-24/`](outputs/eda/2026-10-24/EDA_REPORT.md). Он включает общий текстовый корпус WB + Яндекс Маркет, обязательное сравнение по `source` и отдельный анализ внешнего audit-набора. Исторический notebook и legacy POC остаются во внешнем локальном архиве `../../модель/` только как справочные материалы.

## Правила

- Raw-файлы не редактируются после сохранения. Новая выгрузка получает отдельную датированную папку.
- Для каждого snapshot хранится manifest с источником, Drive ID, временем изменения, форматом, размером и SHA-256.
- Очистка схемы выполняется в `data/interim/`, а готовые train/validation/test datasets — в `data/processed/`.
- Результаты экспериментов не записываются обратно в raw-файлы.
- Персональные идентификаторы авторов отзывов не добавляются.

## Текущая разметка

Snapshot от 20 октября 2026 года: [`data/raw/annotations/2026-10-20/`](data/raw/annotations/2026-10-20/manifest.json).

Обе книги содержат по 1 200 отзывов и листы `Разметка` и `Инструкция`. Наборы `review_id` и порядок строк совпадают. Это неизменяемые исходные ответы разметчиков до adjudication. Нормализованные копии и очередь из 849 уникальных спорных отзывов находятся в [`data/processed/annotations/2026-10-24/`](data/processed/annotations/2026-10-24/), результаты Kappa — в [`outputs/annotation_agreement/2026-10-20/`](outputs/annotation_agreement/2026-10-20/), рабочая книга adjudication — в [`outputs/adjudication/2026-10-20/`](outputs/adjudication/2026-10-20/).

Все пять пограничных правил из [`../docs/research/ANNOTATION_ADJUDICATION_GUIDE_V1.md`](../docs/research/ANNOTATION_ADJUDICATION_GUIDE_V1.md) подтверждены исследователем. AI-assisted решения по всем 849 строкам и коррекция повторяющегося текста повторно проверены и подтверждены исследователем 24 октября. Метод и provenance описаны в [`../docs/research/ADJUDICATION_METHOD_V1.md`](../docs/research/ADJUDICATION_METHOD_V1.md).

Единый `review_level_dataset_v1_1` на 1 200 отзывов находится в [`data/processed/review_level/2026-10-24/`](data/processed/review_level/2026-10-24/manifest.json): 849 строк получили итоговые значения из adjudication, 351 — из полного согласия двух разметчиков.

Пятичастные `review_group_folds_v1_1` заморожены в [`data/processed/splits/2026-10-24/`](data/processed/splits/2026-10-24/manifest.json). Они созданы scikit-learn 1.8.0; все 40 товарных групп входят ровно в один validation-fold. Все последующие эксперименты читают готовый CSV и не пересоздают split.

Snapshot Wildberries от 12 сентября 2026 года: [`data/raw/wildberries/2026-09-12/`](data/raw/wildberries/2026-09-12/manifest.json).

Snapshot публичных отзывов Яндекс Маркета от 21 октября 2026 года: [`data/raw/yandex_market/2026-10-21/`](data/raw/yandex_market/2026-10-21/manifest.json). В raw-пуле 646 уникальных непустых отзывов из шести карточек и шести категорий одежды; имена авторов и профили не сохранялись. Пул ограничен доступными карточками и не является вероятностной выборкой всего Маркета.

Слепой external audit на 300 строк находится в [`data/processed/external_audit/2026-10-21/`](data/processed/external_audit/2026-10-21/manifest.json). Разметка одним исследователем завершена 23 октября 2026 года; актуальный экспорт Google Sheets, русская таблица, нормализованные CSV/JSONL, отчёт проверки и контрольные суммы сохранены в `data/processed/external_audit/2026-10-21/completed/2026-10-23/`. Выборка включает 211 детерминированно отобранных отзывов без fit-keyword и 89 fit-keyword hard cases. Исходная и нормализованная версии проходят схематическую проверку без автоматических исправлений; для `no_signal` используется обязательная явность `none`. Kappa и adjudication для этого single-annotator набора не применяются.

## Итог review-level этапа

В [`outputs/benchmarks/review_level/2026-10-24/`](outputs/benchmarks/review_level/2026-10-24/BENCHMARK_REPORT.md) сохранено сравнение B0, B1, B2, frozen ruBERT и frozen DistilRuBERT на одних пяти folds. Выбрана B2: Signal F1 `0.822`, Direction Macro-F1 `0.754`, 4-class Macro-F1 `0.702`. Замороженная модель, hashes и единая граница confidence/abstain `0.60` находятся в [`config/frozen_review_model_v1.json`](config/frozen_review_model_v1.json).

После заморозки выполнен аудит 300 отзывов Яндекс Маркета: Direction Macro-F1 `0.756`, Signal F1 `0.837`, accuracy `0.830`. Отчёт и построчные прогнозы находятся в [`outputs/external_audit/2026-10-24/`](outputs/external_audit/2026-10-24/YANDEX_EXTERNAL_AUDIT_REPORT.md).

Exploratory item-level pilot на 40 development-группах сохранён в [`outputs/item_level_pilot/2026-10-24/`](outputs/item_level_pilot/2026-10-24/ITEM_LEVEL_PILOT_REPORT.md): equal-weight и informativeness-weighted совпали в 37/40 случаях; 3 решения изменились, победитель без item-level Gold не выбирался.

С 25 октября frozen B2 встроена в продуктовый ML API как backend по умолчанию с equal-weight aggregation; zero-shot сохранён как fallback. Это отдельная интеграция поверх замороженного исследования и не меняет его метрики. Для активации на локальном сайте требуется пересборка ML-контейнера.

Исторический вход для машинной разметки сохранён в `data/interim/wildberries/2026-09-12/reviews_for_model_annotation_v3.jsonl`. Полный результат по канонической схеме v4 находится в [`data/processed/machine_annotations/2026-10-24/`](data/processed/machine_annotations/2026-10-24/manifest.json): 27 384 текста получили machine-generated pseudo-labels, 13 090 пустых записей сохранены как `skipped_empty_text`. Модель, правила, групповые диагностические метрики и контрольные суммы зафиксированы воспроизводимо.
