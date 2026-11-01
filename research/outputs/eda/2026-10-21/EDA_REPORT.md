# EDA AI StyleLink: отзывы и размерное соответствие

Дата анализа: 21 октября 2026 года.

## 1. Использованные данные

- полный snapshot Wildberries: 40,474 отзывов и 40 товарных групп;
- review-level Gold Standard: 1,200 отзывов;
- машинная разметка v4: 27,384 predictions и 13,090 пустых текстов.

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
| fit_label | no_signal | 450 | 0.375 |
| fit_label | true_to_size | 351 | 0.292 |
| fit_label | runs_small | 195 | 0.163 |
| fit_label | runs_large | 204 | 0.170 |
| signal_explicitness | none | 450 | 0.375 |
| signal_explicitness | implicit | 344 | 0.287 |
| signal_explicitness | explicit | 406 | 0.338 |
| informativeness | low | 699 | 0.583 |
| informativeness | medium | 231 | 0.193 |
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
| signal_explicitness | 1.000 | 0.625 | 3 | 0.708 | 0.432 |
| informativeness | 1.000 | 0.417 | 3 | 0.451 | 0.289 |
| body_parameters | 0.774 | 0.176 | 14 | 0.171 | 0.576 |
| fit_zones | 0.756 | 0.222 | 23 | 0.150 | 0.586 |
| user_action | 0.408 | 0.142 | 7 | 0.118 | 0.210 |
| internal_consistency | 0.855 | 0.851 | 4 | 0.068 | 0.082 |

Cramér's V здесь является описательной связью, а не доказательством причинности или полезности в продуктовой модели. Для `signal_explicitness` высокая связь частично задана самой инструкцией: при `no_signal` обязательно ставится `none`.

## 7. Простая абляция

| model | accuracy | macro_f1 | note |
|---|---|---|---|
| text_plus_informativeness | 0.768 | 0.745 | diagnostic upper bound; human auxiliary labels are not production inputs |
| text_plus_all_auxiliary | 0.757 | 0.733 | diagnostic upper bound; human auxiliary labels are not production inputs |
| text_only | 0.685 | 0.692 | text baseline |
| text_plus_action_and_consistency | 0.677 | 0.680 | diagnostic upper bound; human auxiliary labels are not production inputs |
| text_plus_body_and_zones | 0.679 | 0.679 | diagnostic upper bound; human auxiliary labels are not production inputs |
| auxiliary_only | 0.508 | 0.419 | diagnostic upper bound; human auxiliary labels are not production inputs |

Лучшая диагностическая конфигурация — `text_plus_informativeness` с Macro-F1 0.745. Это верхняя оценка: дополнительные признаки взяты из ручной разметки и в реальном inference должны сначала предсказываться. Основную гипотезу об информативности эта таблица не проверяет — для неё требуется item-level сравнение одинаковых review-level predictions с равными и различными весами.

## 8. Машинные pseudo-labels

| fit_label | count | share | mean_confidence | median_confidence |
|---|---|---|---|---|
| no_signal | 24817 | 0.906 | 0.936 | 0.980 |
| true_to_size | 1681 | 0.061 | 0.918 | 0.920 |
| runs_small | 510 | 0.019 | 0.915 | 0.920 |
| runs_large | 376 | 0.014 | 0.915 | 0.920 |

Среди текстовых отзывов `no_signal` занимает 90.6%. Эти значения полезны для exploratory aggregation и формирования hard cases, но не являются Gold Standard.

## 9. Решения после EDA

1. Сохранять короткие отзывы: минимальная длина текста не является фильтром качества fit-сигнала.
2. Считать текущие 40 товарных групп development-корпусом и использовать group folds без пересечения `item_group_id`.
3. Не делать вывод о полезности признака только по Cramér's V; подтверждать его одинаковой group-CV абляцией.
4. `signal_explicitness` не использовать как независимое доказательство fit-класса, поскольку часть связи задана правилами разметки.
5. Информативность сохранить как главный исследуемый вес, но учитывать её низкую исходную Kappa и диагностическое качество предиктора.
6. Следующий внешний аудит формировать только из отзывов Яндекс Маркета, максимум 300 строк, с одной слепой разметкой автора исследования.
7. После появления Яндекс-выгрузки отдельно сравнить длину, пропуски, классы, confidence и ошибки между площадками.
