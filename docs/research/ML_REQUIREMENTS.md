# Требования к ML-модулю

Документ фиксирует минимальный контракт между исследованием и продуктовой интеграцией.

## Границы компонентов

Продуктовый ML включает поиск вещей, совместимость образа и рекомендацию размера. Дипломный эксперимент проверяет только часть, связанную с отзывами о посадке. Выбранная B2 подключена в коде size-shift endpoint по умолчанию; zero-shot сохранён как fallback. Запущенный контейнер получает изменение только после rebuild/restart.

## Вход review-level модели

Обязательные поля:

- `review_id`;
- `item_group_id`;
- `text`.

Ручные признаки разметки не должны быть production-входом основной B2. Пустые тексты не классифицируются и учитываются в Coverage.

## Выход review-level модели

```json
{
  "review_id": "...",
  "label": "runs_small",
  "confidence": 0.81,
  "accepted": true,
  "model_version": "frozen_review_model_v1"
}
```

Допустимые `label`: `no_signal`, `true_to_size`, `runs_small`, `runs_large`. Для замороженной B2 `accepted = confidence >= 0.60`.

## Замороженная конфигурация

- Модель: word/char TF-IDF + class-balanced Logistic Regression.
- Версия данных: `review_level_dataset_v1_1`.
- Split: `review_group_folds_v1_1`.
- Порог confidence/abstain: `0.60`.
- Конфигурация и hashes: [`../../research/config/frozen_review_model_v1.json`](../../research/config/frozen_review_model_v1.json).

Изменение данных, признаков, параметров или порога требует новой версии модели и повторной validation-оценки. Yandex audit нельзя использовать для настройки.

## Item-level агрегация

Агрегатор получает только принятые review-level прогнозы одной версии модели.

- Equal-weight: вес каждого отзыва `1`.
- Informativeness-weighted: `high = 2`, `not_high = 1`.
- При недостаточном или противоречивом сигнале возвращается `abstain`.

Текущий pilot не определил лучший метод. До появления item-level Gold production-вариантом следует считать более простой equal-weight, а weighted хранить как экспериментальный.

Текущая реализация B2:

- берёт до 20 уникальных пар `текст + заказанный размер` на товар;
- не использует keyword-фильтр;
- принимает направленный review-сигнал при `confidence >= 0.60` и классе не `no_signal`;
- нормализует вероятности по трём направлениям и усредняет их с одинаковым весом;
- возвращает ответ при item-level confidence `>= 0.60`, иначе `insufficient_evidence`;
- оставляет `recommended_size = null`.

Это продуктовая реализация exploratory equal-weight метода, а не доказательство его item-level точности.

## Ответ item-level сервиса

```json
{
  "item_group_id": "...",
  "fit_signal": "runs_small",
  "confidence": 0.74,
  "abstain": false,
  "accepted_reviews": 8,
  "aggregation": "equal_weight",
  "review_model_version": "frozen_review_model_v1"
}
```

Персональный `recommended_size` не выводится без параметров пользователя и размерной сетки.

## Оценка

Review-level:

- Signal F1;
- Direction Macro-F1;
- precision/recall по классам;
- confusion matrix;
- calibration и Risk@Coverage;
- размер модели и время инференса.

Item-level при наличии независимого Gold:

- Error Rate и Macro-F1;
- Coverage;
- Risk@Coverage;
- парное сравнение equal-weight и weighted на одинаковых прогнозах.

## Воспроизводимость

- Использовать замороженные folds и версии артефактов.
- Хранить manifest, SHA-256, параметры среды и model version.
- Не перезаписывать raw, Gold, frozen model и отчёты.
- Отделять offline research metrics от поведения локального сайта.

## Переключение реализации

- `FIT_MODEL_BACKEND=b2` — замороженная B2, значение по умолчанию.
- `FIT_MODEL_BACKEND=zero_shot` — прежний MiniLM fallback.
- Артефакт B2 проверяется по SHA-256 до загрузки.
- Активное значение доступно в `GET /health` как `fit_backend`.
- Изменение настройки требует rebuild/restart ML-контейнера.
