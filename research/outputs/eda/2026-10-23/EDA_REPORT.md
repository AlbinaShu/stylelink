# EDA AI StyleLink: отзывы и размерное соответствие

Дата анализа: 23 октября 2026 года.

## 1. Использованные данные

- полный snapshot Wildberries: 40,474 отзывов и 40 товарных групп;
- snapshot Яндекс Маркета: 646 непустых отзывов, 6 карточек и 6 категорий одежды;
- review-level Gold Standard: 1,200 отзывов;
- машинная разметка v4: 27,384 predictions и 13,090 пустых текстов.
- внешний аудит Яндекс Маркета: 300 отзывов с разметкой одного исследователя.

## 2. Качество и структура полного snapshot

| metric | value |
|---|---|
| rows | 40474.000 |
| unique_review_ids | 40474.000 |
| duplicate_review_ids | 0.000 |
| item_groups | 40.000 |
| nm_ids | 531.000 |
| reviews_with_text | 27384.000 |
| reviews_without_text | 13090.000 |
| reviews_with_ordered_size | 40452.000 |
| reviews_with_fit_keyword | 2979.000 |
| duplicate_nonempty_texts | 2605.000 |
| median_words_nonempty | 8.000 |
| mean_words_nonempty | 11.160 |

В данных не обнаружены дубликаты `review_id`. Пустые тексты составляют 32.3% snapshot и должны оставаться в знаменателе Coverage, но не подаваться текстовой модели. Медианная длина непустого отзыва — 8 слов.

## 3. Репрезентативность ручной разметки

| dataset | n | fit_keyword_share | median_words | mean_rating |
|---|---|---|---|---|
| all_nonempty_wb | 27384 | 0.109 | 8.000 | 4.559 |
| manual_gold | 1200 | 1.000 | 24.000 | 4.655 |

Ручной Gold Standard существенно длиннее полного пула: медиана 24 против 8 слов. Доля fit-keyword составляет 100.0% против 10.9%. Поэтому текущие 1 200 строк подходят для разработки классификатора направления, но не дают несмещённой end-to-end оценки обнаружения fit-сигнала.

## 4. Распределение ручных меток

| field | value | count | share |
|---|---|---|---|
| fit_label | no_signal | 449 | 0.374 |
| fit_label | true_to_size | 352 | 0.293 |
| fit_label | runs_small | 195 | 0.163 |
| fit_label | runs_large | 204 | 0.170 |
| signal_explicitness | none | 449 | 0.374 |
| signal_explicitness | implicit | 345 | 0.287 |
| signal_explicitness | explicit | 406 | 0.338 |
| informativeness | low | 698 | 0.582 |
| informativeness | medium | 232 | 0.193 |
| informativeness | high | 270 | 0.225 |

## 5. Согласованность разметки до adjudication

| field | n_pairs | observed_agreement | cohens_kappa |
|---|---|---|---|
| fit_label | 1200 | 0.704 | 0.591 |
| signal_explicitness | 1200 | 0.626 | 0.432 |
| informativeness | 1200 | 0.539 | 0.289 |
| user_action | 1198 | 0.409 | 0.210 |
| internal_consistency | 1196 | 0.858 | 0.082 |
| body_parameters_exact_set | 1198 | 0.775 | 0.576 |
| fit_zones_exact_set | 1200 | 0.756 | 0.586 |
| signal_vs_no_signal | 1200 | 0.792 | 0.389 |
| fit_direction_both_signal | 824 | 0.871 | 0.799 |
| informativeness_quadratic | 1197 | 0.541 | 0.511 |

Направление посадки при наличии сигнала размечается заметно стабильнее, чем граница `signal/no_signal`, действие пользователя, внутренняя согласованность и информативность. Это объясняет необходимость v4 и отдельного хранения исходных ответов.

## 6. Диагностика размеченных признаков

| feature | resolved_coverage | non_default_or_nonempty_share | n_states_including_unresolved | cramers_v_with_fit_label | pre_adjudication_kappa |
|---|---|---|---|---|---|
| signal_explicitness | 1.000 | 0.626 | 3 | 0.708 | 0.432 |
| informativeness | 1.000 | 0.418 | 3 | 0.451 | 0.289 |
| body_parameters | 0.774 | 0.176 | 14 | 0.171 | 0.576 |
| fit_zones | 0.756 | 0.222 | 23 | 0.150 | 0.586 |
| user_action | 0.408 | 0.142 | 7 | 0.119 | 0.210 |
| internal_consistency | 0.855 | 0.851 | 4 | 0.068 | 0.082 |

Cramér's V здесь является описательной связью, а не доказательством причинности или полезности в продуктовой модели. Для `signal_explicitness` высокая связь частично задана самой инструкцией: при `no_signal` обязательно ставится `none`.

## 7. Простая абляция

| model | accuracy | macro_f1 | note |
|---|---|---|---|
| text_plus_all_auxiliary | 0.769 | 0.747 | diagnostic upper bound; human auxiliary labels are not production inputs |
| text_plus_informativeness | 0.765 | 0.743 | diagnostic upper bound; human auxiliary labels are not production inputs |
| text_only | 0.686 | 0.691 | text baseline |
| text_plus_action_and_consistency | 0.684 | 0.688 | diagnostic upper bound; human auxiliary labels are not production inputs |
| text_plus_body_and_zones | 0.683 | 0.683 | diagnostic upper bound; human auxiliary labels are not production inputs |
| auxiliary_only | 0.527 | 0.433 | diagnostic upper bound; human auxiliary labels are not production inputs |

Лучшая диагностическая конфигурация — `text_plus_all_auxiliary` с Macro-F1 0.747. Это верхняя оценка: дополнительные признаки взяты из ручной разметки и в реальном inference должны сначала предсказываться. Основную гипотезу об информативности эта таблица не проверяет — для неё требуется item-level сравнение одинаковых review-level predictions с равными и различными весами.

## 8. Машинные pseudo-labels

| fit_label | count | share | mean_confidence | median_confidence |
|---|---|---|---|---|
| no_signal | 24817 | 0.906 | 0.936 | 0.980 |
| true_to_size | 1681 | 0.061 | 0.918 | 0.920 |
| runs_small | 510 | 0.019 | 0.915 | 0.920 |
| runs_large | 376 | 0.014 | 0.915 | 0.920 |

Среди текстовых отзывов `no_signal` занимает 90.6%. Эти значения полезны для exploratory aggregation и формирования hard cases, но не являются Gold Standard.

## 9. Сравнение Wildberries и Яндекс Маркета

| source | nonempty_reviews | product_groups | mean_words | median_words | p90_words | shorter_than_10_words_share | ordered_size_coverage | common_fit_keyword_share | duplicate_text_share |
|---|---|---|---|---|---|---|---|---|---|
| wildberries | 27384 | 40 | 11.160 | 8.000 | 24.000 | 0.597 | 0.999 | 0.338 | 0.095 |
| yandex_market | 646 | 6 | 18.975 | 14.000 | 39.000 | 0.324 | 1.000 | 0.393 | 0.015 |

Общий текстовый корпус содержит 28,030 непустых отзывов, но источник сохраняется для каждой строки. Медиана длины составляет 8 слов для Wildberries и 14 слов для Яндекс Маркета. Доля текстов короче 10 слов — 59.7% и 32.4% соответственно. Это показывает domain shift по форме текста; сводная статистика без разбивки по площадкам скрыла бы различия.

Единый простой словарь fit-упоминаний применяется к обеим площадкам только как EDA-индикатор, а не как разметка или target. Он встречается в 33.8% текстов Wildberries и 39.3% текстов Яндекс Маркета.

### Яндекс Маркет по категориям

| category | reviews | products | median_words | mean_words | common_fit_keyword_share |
|---|---|---|---|---|---|
| jeans | 164 | 1 | 10.000 | 14.829 | 0.445 |
| sports_tshirt | 157 | 1 | 17.000 | 21.529 | 0.312 |
| outerwear | 101 | 1 | 15.000 | 20.584 | 0.228 |
| jumper | 100 | 1 | 18.000 | 21.610 | 0.500 |
| sweatshirt | 85 | 1 | 12.000 | 16.035 | 0.506 |
| trousers | 39 | 1 | 12.000 | 21.615 | 0.410 |

Пул Яндекс Маркета ограничен шестью карточками: каждая категория представлена одной карточкой. Поэтому различия категорий нельзя отделить от различий конкретных товаров, а найденные доли нельзя переносить на весь маркетплейс.

## 10. Размеченный внешний аудит Яндекс Маркета

| field | value | count | share |
|---|---|---|---|
| fit_label | no_signal | 197 | 0.657 |
| fit_label | true_to_size | 34 | 0.113 |
| fit_label | runs_small | 37 | 0.123 |
| fit_label | runs_large | 32 | 0.107 |
| signal_explicitness | none | 197 | 0.657 |
| signal_explicitness | implicit | 29 | 0.097 |
| signal_explicitness | explicit | 74 | 0.247 |
| informativeness | low | 242 | 0.807 |
| informativeness | medium | 42 | 0.140 |
| informativeness | high | 16 | 0.053 |

### По стратам отбора

| selection_stratum | reviews | signal_share | explicit_or_implicit_share | medium_or_high_informativeness_share | median_words |
|---|---|---|---|---|---|
| fit_keyword | 89 | 0.899 | 0.899 | 0.371 | 20.000 |
| random_no_keyword | 211 | 0.109 | 0.109 | 0.118 | 14.000 |

Внешний аудит содержит 197 `no_signal`, 34 `true_to_size`, 37 `runs_small` и 32 `runs_large`. Это single-annotator audit: Cohen's Kappa и adjudication к нему не применяются. Его метки не используются для переопределения признаков или выбора модели до основной внешней оценки; после фиксации модели они применяются для проверки переноса и анализа ошибок.

## 11. Решения после EDA

1. Сохранять короткие отзывы: минимальная длина текста не является фильтром качества fit-сигнала.
2. Считать текущие 40 товарных групп development-корпусом и использовать group folds без пересечения `item_group_id`.
3. Не делать вывод о полезности признака только по Cramér's V; подтверждать его одинаковой group-CV абляцией.
4. `signal_explicitness` не использовать как независимое доказательство fit-класса, поскольку часть связи задана правилами разметки.
5. Информативность сохранить как главный исследуемый вес, но учитывать её низкую исходную Kappa и диагностическое качество предиктора.
6. Общий текстовый EDA проводить на WB и Яндекс Маркете совместно, но всегда сохранять поле источника и показывать сравнение площадок отдельно.
7. Все 646 отзывов Яндекс Маркета использовать только для описательной статистики текста; 300 размеченных строк хранить отдельно как внешний аудит.
8. Не использовать метки внешнего аудита для изменения признаков, правил или выбора модели до фиксации основного review-level протокола.
9. После фиксации модели рассчитать на 300 строках Яндекса метрики переноса, confidence/calibration и error analysis.
