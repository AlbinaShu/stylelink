# Binary informativeness target

`review_level_informativeness_binary_v1.csv` — замороженная производная цель для основного эксперимента:

```text
high -> high
low + medium -> not_high
```

Артефакт содержит 1 200 `review_id`: 270 `high` и 930 `not_high`. Исходное трёхуровневое поле `informativeness` из Gold Standard v1.1 сохранено в отдельной колонке и не изменено.

Контрольные суммы, источник, mapping и версия генератора находятся в `manifest.json`. Этот target используется только в явно версионированных экспериментах; он не заменяет Gold Standard.
