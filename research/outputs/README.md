# Research outputs

Метрики, графики, таблицы и отчёты экспериментов. Каждый результат должен ссылаться на версию processed dataset, конфигурацию модели и commit кода.

`annotation_agreement/2026-10-20/` содержит отчёты Cohen’s Kappa для нормализованной двойной разметки v3 до adjudication.

`adjudication/2026-10-20/` содержит завершённую книгу `adjudication_primary_v1.xlsx` с инструкцией и 849 уникальными спорными отзывами. Все строки имеют статус `complete`; provenance решений сохранён в книге и manifest.

`eda/2026-10-21/` сохранён как предыдущая версия EDA только по Wildberries.

`eda/2026-10-24/` содержит актуальный межплатформенный EDA: Markdown-отчёт, PNG-графики, CSV-таблицы, сравнение WB и Яндекс Маркета, отдельный анализ внешнего audit-набора, результаты простой ablation-проверки и manifest с контрольными суммами.

`benchmarks/review_level/2026-10-24/` содержит OOF predictions и метрики B0, B1, B2, frozen ruBERT и frozen DistilRuBERT, classifier artifacts, confusion matrices, reliability diagram, threshold/coverage plot и итоговый отчёт. Выбрана B2; frozen-конфигурация хранится в `research/config/frozen_review_model_v1.json`.

`benchmarks/informativeness/2026-10-24/` содержит бинарный служебный benchmark `high` против `not_high`, использованный в exploratory item-level pilot.

`external_audit/2026-10-24/` содержит однократную оценку замороженной B2 на 300 размеченных отзывах Яндекс Маркета: построчные predictions, общие и постратовые метрики, transfer comparison и manifest.

`item_level_pilot/2026-10-24/` содержит exploratory-сравнение equal-weight и `high=2 / not_high=1` на 40 development-группах. Item-level accuracy там намеренно отсутствует: независимого item-level Gold Standard нет.
