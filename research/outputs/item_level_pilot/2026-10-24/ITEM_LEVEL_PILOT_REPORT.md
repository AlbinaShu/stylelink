# Exploratory item-level pilot

Pilot проведён на 40 текущих development-группах без item-level Gold Standard. Оба метода используют одни прогнозы замороженной B2, один review-level фильтр `confidence >= 0.60`, одну формулу класса и одну границу item-level `0.60`. Различается только вес: `1` против `high=2 / not_high=1`.

## Результат

- Совпавший итоговый verdict: 37 из 40 групп (`0.925`).
- Изменившийся verdict или answer/abstain: 3 групп.
- Abstain: equal-weight — 23, weighted — 24 групп.
- Средний confidence: equal-weight `0.583`, weighted `0.565`.
- Среднее число направленных evidence-отзывов на группу: `95.1`.

## Расхождения

| item_group_id | evidence | high | equal | conf | weighted | conf |
|---|---:|---:|---|---:|---|---:|
| `13456309` | 132 | 29 | abstain | 0.586 | runs_small | 0.627 |
| `320743306` | 111 | 32 | true_to_size | 0.635 | abstain | 0.591 |
| `948936376` | 120 | 14 | true_to_size | 0.624 | abstain | 0.596 |

Эти числа показывают чувствительность агрегированного решения к весам, но не точность. Без независимого item-level Gold нельзя утверждать, какой вариант лучше, и победитель не выбирается.
