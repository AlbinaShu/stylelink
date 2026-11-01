#!/usr/bin/env python3
"""Build the readable EDA notebook from the reproducible analysis module."""
from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = PROJECT_ROOT / "research/notebooks/01_review_fit_eda.ipynb"
CELL_INDEX = 0


def lines(text: str) -> list[str]:
    return [line + "\n" for line in text.strip().splitlines()]


def next_cell_id(prefix: str) -> str:
    global CELL_INDEX
    CELL_INDEX += 1
    return f"{prefix}-{CELL_INDEX:03d}"


def markdown(text: str) -> dict:
    return {"cell_type": "markdown", "id": next_cell_id("md"), "metadata": {}, "source": lines(text)}


def code(text: str) -> dict:
    return {"cell_type": "code", "id": next_cell_id("code"), "execution_count": None, "metadata": {}, "outputs": [], "source": lines(text)}


cells = [
    markdown(
        """
# EDA: отзывы и размерное соответствие AI StyleLink

Ноутбук отвечает на шесть практических вопросов:

1. как устроен полный snapshot Wildberries;
2. насколько ручной Gold Standard репрезентативен;
3. согласованно ли размечены дополнительные признаки;
4. дают ли эти признаки диагностический прирост к простой текстовой модели;
5. чем отличаются тексты Wildberries и Яндекс Маркета;
6. как устроен размеченный внешний аудит Яндекс Маркета.

Анализ намеренно остаётся понятным и воспроизводимым: описательные статистики, простые графики, Cramér's V и одна групповая ablation-проверка.
"""
    ),
    markdown(
        """
## 1. Методика

EDA разделён на три уровня:

- полный snapshot описывает качество, пропуски и естественное распределение отзывов;
- общий текстовый EDA объединяет непустые отзывы WB и Яндекс Маркета, но всегда сохраняет `source` и показывает площадки отдельно;
- ручной Gold Standard используется для анализа targets, согласованности и размеченных признаков;
- 300 размеченных отзывов Яндекс Маркета рассматриваются отдельно как single-annotator external audit.

Machine-generated pseudo-labels анализируются отдельно и не считаются Gold Standard. Все model diagnostics используют групповые folds по `item_group_id`, чтобы отзывы одного товара не пересекали train и validation. Метки внешнего аудита не используются для изменения признаков, правил или выбора модели до основной оценки переноса.
"""
    ),
    code(
        """
from pathlib import Path
import sys
import pandas as pd
from IPython.display import Image, Markdown, display

def find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "research/data").exists() and (candidate / "docs/research").exists():
            return candidate
    raise RuntimeError("Не найден корень проекта ai-stylelink")

PROJECT_ROOT = find_project_root(Path.cwd().resolve())
sys.path.insert(0, str(PROJECT_ROOT))

from research.src.analysis.run_review_fit_eda import run_eda

pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 140)
OUTPUT_DIR = PROJECT_ROOT / "research/outputs/eda/2026-10-24"
result = run_eda(output_dir=OUTPUT_DIR)
print(f"Проект: {PROJECT_ROOT}")
print(f"Результаты: {OUTPUT_DIR}")
"""
    ),
    markdown("## 2. Загрузка и проверка единиц анализа"),
    code(
        """
raw = result["raw"]
gold = result["gold"]
machine = result["machine"]
yandex_raw = result["yandex_raw"]
yandex_audit = result["yandex_audit"]

pd.DataFrame([
    {"dataset": "raw_wildberries", "rows": len(raw), "unique_reviews": raw.review_id.nunique(), "item_groups": raw.root_id.nunique()},
    {"dataset": "review_level_gold", "rows": len(gold), "unique_reviews": gold.review_id.nunique(), "item_groups": gold.item_group_id.nunique()},
    {"dataset": "machine_annotations", "rows": len(machine), "unique_reviews": machine.review_id.nunique(), "item_groups": machine.item_group_id.nunique()},
    {"dataset": "raw_yandex_market", "rows": len(yandex_raw), "unique_reviews": yandex_raw.review_id.nunique(), "item_groups": yandex_raw.product_group_id.nunique()},
    {"dataset": "yandex_market_external_audit", "rows": len(yandex_audit), "unique_reviews": yandex_audit.review_id.nunique(), "item_groups": yandex_audit.product_id.nunique()},
])
"""
    ),
    code('result["tables"]["full_data_summary"]'),
    markdown(
        """
### Выводы по этапу

- Ключ `review_id` уникален во всех 40 474 строках.
- Основная item-level единица — `root_id`/`item_group_id`; в snapshot всего 40 таких групп.
- 13 090 отзывов не имеют текста. Они не подаются text-модели, но сохраняются для расчёта Coverage.
- Повторяющиеся тексты существуют, поэтому при дальнейшем обучении полезно отдельно контролировать текстовые дубликаты внутри folds.
"""
    ),
    markdown("## 3. Длина текста и смещение ручной выборки"),
    code('result["tables"]["text_length_comparison"]'),
    code('display(Image(filename=str(OUTPUT_DIR / "figures/01_text_length_comparison.png")))'),
    code('result["tables"]["selection_bias"]'),
    markdown(
        """
### Выводы по этапу

- В полном пуле медиана равна 8 словам, в ручном Gold Standard — 24 словам.
- Fit-keyword присутствует в 100% ручной выборки и только примерно в 10,9% полного пригодного пула.
- Поэтому текущие 1 200 строк подходят для разработки направления посадки, но завышают ожидаемое end-to-end качество обнаружения fit-сигнала.
- Автоматически удалять короткие отзывы нельзя: короткая фраза может содержать прямой сильный сигнал.
"""
    ),
    markdown("## 4. Распределение ручных targets"),
    code('result["tables"]["gold_distribution"]'),
    code('display(Image(filename=str(OUTPUT_DIR / "figures/02_gold_fit_distribution.png")))'),
    markdown(
        """
### Выводы по этапу

- Все четыре fit-класса представлены, хотя `no_signal` является крупнейшим классом.
- 58,3% отзывов получили низкую информативность.
- Для модели нужны class weights или контролируемая стратификация, а качество следует показывать через Macro-F1, а не только Accuracy.
"""
    ),
    markdown("## 5. Согласованность разметчиков до adjudication"),
    code('result["tables"]["annotation_agreement"]'),
    markdown(
        """
### Выводы по этапу

- Четыре fit-метки имеют умеренную согласованность.
- После того как оба разметчика признали наличие сигнала, направление определяется заметно стабильнее.
- Самые проблемные признаки — действие пользователя, внутренняя согласованность и информативность.
- Значения рассчитаны до обсуждения расхождений; итоговый Gold Standard хранится отдельно.
"""
    ),
    markdown("## 6. Покрытие и описательная связь размеченных признаков"),
    code('result["tables"]["feature_diagnostics"]'),
    code(
        """
display(Image(filename=str(OUTPUT_DIR / "figures/04_auxiliary_feature_coverage.png")))
display(Image(filename=str(OUTPUT_DIR / "figures/05_feature_cramers_v.png")))
"""
    ),
    markdown(
        """
### Выводы по этапу

- `signal_explicitness` сильно связан с fit-меткой, но часть связи задана инструкцией: для `no_signal` обязательно используется `none`. Это не независимое доказательство полезности.
- `informativeness` показывает наиболее заметную нетривиальную связь с fit-классом, но её исходная Kappa остаётся низкой.
- Параметры тела и зоны посадки размечаются сравнительно устойчиво, однако встречаются нечасто и имеют слабую связь с общим fit-классом.
- Действие пользователя имеет низкое покрытие и низкую согласованность.
- Внутренняя согласованность почти не связана с fit-классом и в текущем виде не выглядит сильным основным признаком.
"""
    ),
    markdown("## 7. Простая ablation-проверка"),
    code('result["tables"]["ablation_results"]'),
    code('display(Image(filename=str(OUTPUT_DIR / "figures/06_ablation_macro_f1.png")))'),
    markdown(
        """
### Выводы по этапу

- Простой text-only baseline получает Macro-F1 около 0,692.
- Добавление ручной информативности повышает диагностический результат примерно до 0,745.
- Параметры тела и зоны, а также действие и согласованность по отдельности не улучшают text baseline.
- Все дополнительные признаки вместе дают меньший результат, чем одна информативность.

Это **диагностическая верхняя оценка**: здесь используются ручные признаки. В production их сначала должна предсказать модель. Поэтому таблица поддерживает решение оставить информативность основной исследуемой переменной, но ещё не подтверждает item-level гипотезу.
"""
    ),
    markdown("## 8. Полная машинная разметка"),
    code('result["tables"]["machine_distribution"]'),
    code(
        """
display(Image(filename=str(OUTPUT_DIR / "figures/03_machine_fit_distribution.png")))
display(Image(filename=str(OUTPUT_DIR / "figures/08_machine_confidence_by_label.png")))
"""
    ),
    markdown(
        """
### Выводы по этапу

- В полном текстовом пуле 90,6% отзывов получили `no_signal`.
- Это правдоподобно с учётом естественного потока отзывов, но confidence частично задаётся строгими правилами v4 и не является откалиброванной вероятностью.
- Machine labels можно использовать для exploratory aggregation, формирования hard cases и анализа покрытия, но не как финальный Gold Standard.
"""
    ),
    markdown("## 9. Wildberries и Яндекс Маркет: общий и сравнительный EDA"),
    code('result["tables"]["combined_text_summary"]'),
    code('result["tables"]["marketplace_text_summary"]'),
    code(
        """
display(Image(filename=str(OUTPUT_DIR / "figures/09_marketplace_text_length.png")))
display(Image(filename=str(OUTPUT_DIR / "figures/11_marketplace_fit_keyword_share.png")))
"""
    ),
    markdown(
        """
### Выводы по этапу

- Общий текстовый EDA охватывает все непустые отзывы обеих площадок, но `source` сохраняется для каждой строки.
- Сравнение площадок обязательно: единая сводка скрывает различия длины текста, доли коротких отзывов и частоты fit-слов.
- Fit-словарь здесь используется только как одинаковый описательный индикатор и не заменяет ручную разметку.
"""
    ),
    markdown("### Яндекс Маркет по категориям"),
    code('result["tables"]["yandex_category_summary"]'),
    markdown(
        """
Каждая из шести категорий Яндекс Маркета представлена одной карточкой. Поэтому различия категорий одновременно являются различиями конкретных товаров и не оценивают весь маркетплейс.
"""
    ),
    markdown("## 10. Размеченный внешний аудит Яндекс Маркета"),
    code('result["tables"]["yandex_audit_distribution"]'),
    code('result["tables"]["yandex_audit_by_stratum"]'),
    code('display(Image(filename=str(OUTPUT_DIR / "figures/10_yandex_audit_fit_distribution.png")))'),
    markdown(
        """
### Выводы по этапу

- Все 300 строк размечены одним исследователем; Kappa и adjudication для этого набора не применяются.
- Внешний аудит хранится отдельно от development Gold Standard.
- Его метки не должны влиять на выбор признаков, правил и модели до фиксации основного протокола. После этого они используются для оценки переноса между площадками и анализа ошибок.
"""
    ),
    markdown("## 11. Число отзывов на товар"),
    code('display(Image(filename=str(OUTPUT_DIR / "figures/07_reviews_per_item_group.png")))'),
    markdown(
        """
### Выводы по этапу

Товарные группы различаются по числу отзывов, поэтому при item-level агрегации нельзя считать отдельные отзывы независимыми наблюдениями. Split, bootstrap и доверительные интервалы должны строиться по `item_group_id`.
"""
    ),
    markdown("## 12. Итоговые решения"),
    markdown(
        """
1. Основным review-level target остаётся fit-класс, а информативность — главным кандидатом на вес при item-level агрегации.
2. Параметры тела, зоны, действие и согласованность не удаляются из схемы, но переносятся в дополнительные ablation-эксперименты.
3. Низкая Kappa информативности требует осторожной интерпретации и отдельной оценки её предиктора.
4. Текущие 40 товарных групп считаются development-корпусом.
5. Общий текстовый EDA включает WB и Яндекс Маркет, но все выводы также показываются отдельно по `source`.
6. Все 646 отзывов Яндекса используются для описательного анализа, а 300 размеченных строк остаются отдельным внешним аудитом.
7. Метки Яндекса не используются для настройки модели до фиксации review-level протокола.
8. Основная гипотеза будет проверяться сравнением equal-weight и informativeness-weighted aggregation на одинаковых review-level probabilities.
"""
    ),
    markdown("## 13. Полный автоматически сформированный отчёт"),
    code('display(Markdown((OUTPUT_DIR / "EDA_REPORT.md").read_text(encoding="utf-8")))'),
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(OUTPUT)
