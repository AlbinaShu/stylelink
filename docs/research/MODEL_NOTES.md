# Модели и гипотеза

## Исследовательская постановка

Количественно проверяется качество определения посадки по отдельному отзыву. Дополнительно, в exploratory-режиме, проверяется, меняет ли бинарное взвешивание отзывов по информативности итог товара относительно equal-weight aggregation.

Преимущество weighted aggregation по item-level accuracy сейчас не заявляется: независимого item-level Gold Standard нет.

## Review-level задача

Модель предсказывает один из четырёх классов:

- `no_signal`;
- `true_to_size`;
- `runs_small`;
- `runs_large`.

Оценка разделена на три блока:

1. Signal F1 для `signal/no_signal`.
2. Direction Macro-F1 для трёх направлений на строках с Gold-сигналом; пропуск сигнала считается ошибкой.
3. 4-class Macro-F1 как вторичная сводная метрика.

## Сравнённые модели

- B0: всегда `no_signal`;
- B1: словарные правила;
- B2: word/char TF-IDF + class-balanced Logistic Regression;
- frozen ruBERT CLS + Logistic Regression;
- frozen DistilRuBERT CLS + Logistic Regression.

Все модели оценены на одинаковых пяти frozen group folds. Full fine-tuning трансформеров не проводился.

B2 выбрана по Direction Macro-F1 `0.754`; она также компактнее и быстрее transformer-вариантов. Полная таблица находится в [RESEARCH_STATUS.md](RESEARCH_STATUS.md).

## Confidence и abstain

Для B2 заморожена единая граница `0.60`:

- `confidence >= 0.60` — прогноз принимается;
- `confidence < 0.60` — `abstain`.

Порог выбран до внешнего аудита и не перенастраивался на Яндекс Маркете. Confidence нельзя трактовать как гарантированную вероятность корректности вне проверенного корпуса.

## Informativeness

Для агрегации используется бинарная служебная цель:

- `high` → вес `2`;
- `low` или `medium` → `not_high`, вес `1`.

Классификатор дал F1 для `high = 0.526`, Macro-F1 `0.689`, PR AUC `0.511`. Этого достаточно только для exploratory pilot, не для утверждения о production-качестве весов.

## Item-level aggregation

Обе стратегии получают одинаковые review-level прогнозы B2.

- Equal-weight: каждый принятый отзыв имеет вес `1`.
- Weighted: `high = 2`, `not_high = 1`.

В pilot на 40 товарах verdict совпал в 37 случаях. Weighted-вариант дал 24 abstain против 23 и средний confidence `0.565` против `0.583`. Без item-level Gold это показывает чувствительность результата к весам, но не улучшение качества.

## Связь с продуктом

В код локального ML API встроена замороженная B2 и выбрана по умолчанию, а zero-shot MiniLM сохранён как fallback; детали переключения находятся в [`../../ml/`](../../ml/README.md). Для применения изменений на запущенном сайте требуется пересборка ML-контейнера. Fit shift сам по себе не даёт персональный S/M/L: нужны параметры пользователя и размерная сетка товара.
