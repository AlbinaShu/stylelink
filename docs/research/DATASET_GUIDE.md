# Данные исследования

## Зафиксированные наборы

| Набор | Состав | Назначение |
|---|---:|---|
| `review_level_dataset_v1_1` | 1 200 отзывов, 40 WB-групп | обучение и 5-fold OOF-оценка |
| `review_group_folds_v1_1` | 5 folds | замороженное разбиение по `item_group_id` |
| WB snapshot | 40 474 записей, 27 384 непустых текста | pseudo-labels и item-level pilot |
| Yandex external audit | 300 отзывов из 6 карточек | проверка переноса после заморозки модели |

Gold Standard v1.1 содержит:

- `no_signal` — 449;
- `true_to_size` — 352;
- `runs_small` — 195;
- `runs_large` — 204.

Канонические файлы и manifests находятся в [`../../research/data/`](../../research/data/README.md). Raw-snapshots неизменяемы; исправленная цепочка сохранена отдельной версией от `2026-10-24` и не перезаписывает прежние данные.

## Review-level схема

Обязательные поля для эксперимента:

- `review_id` — стабильный идентификатор строки;
- `item_group_id` — группа товара для split;
- `text` — текст отзыва;
- `fit_label` — `no_signal`, `true_to_size`, `runs_small` или `runs_large`;
- `fit_code` — согласованный числовой код;
- `signal_explicitness` — `none`, `implicit` или `explicit`;
- `informativeness` — `low`, `medium` или `high`.

Связанные поля должны быть логически согласованы. Для `no_signal` используется `signal_explicitness = none`. Метка `true_to_size` означает свидетельство о соответствии размера, а не отсутствие информации.

## Происхождение Gold Standard

Два разметчика независимо обработали одинаковые 1 200 отзывов. Совпавшие ответы приняты напрямую; спорные строки прошли AI-assisted adjudication и были подтверждены исследователем. Эти решения считаются Gold Standard текущего проекта. Raw-разметка не редактировалась.

Метод описан в [ADJUDICATION_METHOD_V1.md](ADJUDICATION_METHOD_V1.md), правила — в [ANNOTATION_GUIDE_V4.md](ANNOTATION_GUIDE_V4.md) и [ANNOTATION_ADJUDICATION_GUIDE_V1.md](ANNOTATION_ADJUDICATION_GUIDE_V1.md).

## Split и защита от leakage

- Все отзывы одной `item_group_id` принадлежат одному validation-fold.
- Все 1 200 строк входят ровно в один из пяти folds.
- Downstream-эксперименты читают сохранённый CSV и не пересоздают split.
- Новый split допустим только как новая явно названная версия.

## Яндекс Маркет

External audit сформирован до просмотра модельных ошибок и размечен одним исследователем:

- `fit_keyword` — 89 сложных отзывов с fit-лексикой;
- `random_no_keyword` — 211 детерминированно выбранных отзывов без fit-keyword.

Выборка нужна для проверки переноса WB → Яндекс Маркет. Она не является вероятностной выборкой маркетплейса: охвачены только шесть карточек, а в `random_no_keyword` мало Gold-сигналов и представлен один класс направления.

## Pseudo-labels и item-level данные

На полном WB snapshot моделью размечены 27 384 непустых текста; 13 090 пустых записей сохранены как `skipped_empty_text`. Эти прогнозы используются для exploratory aggregation, но не являются Gold Standard.

Независимой item-level разметки нет. Поэтому на текущих 40 товарах можно сравнивать только agreement, изменения verdict, confidence и abstain, но нельзя считать item-level accuracy или объявлять лучший способ агрегации.

## Правила использования

- Не изменять файлы в `raw/` и замороженные версии processed-данных.
- Для новой версии создавать новую датированную папку и manifest с SHA-256.
- Не подбирать модель или порог по внешнему Yandex audit.
- Не смешивать review-level Gold, item-level прогноз и pseudo-labels.
- Не добавлять персональные данные авторов отзывов.
