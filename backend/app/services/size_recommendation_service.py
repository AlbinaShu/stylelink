import re
from typing import Any


class SizeRecommendationService:
    """Backend-логика работы с размерным рядом продавца."""


    # STYLELINK_UNIVERSAL_SIZE_SELECTION_V1

    @staticmethod
    def size_numbers(value: str | None) -> set[int] | None:
        """
        Безопасное сопоставление RU-размеров.

        Поддержка:
        50
        RU 50
        50(65)
        50 (65)
        50/170
        48-50
        40 - 25.5 см

        Неизвестные форматы не угадываем.
        """
        if value is None:
            return None

        raw = str(value).strip().upper()

        if not raw:
            return None

        raw = re.sub(r"^RU\s*", "", raw)

        # Размер + дополнительный параметр в скобках.
        raw = re.sub(
            r"\s*\(\s*\d{2,3}\s*\)\s*$",
            "",
            raw,
        )

        # Размер + рост.
        raw = re.sub(
            r"\s*[/\-–—]\s*(?:1\d{2}|2\d{2})$",
            "",
            raw,
        )

        # RU-размер обуви с обозначением Р. и длиной стельки.
        match = re.fullmatch(
            r"(\d{2})\s*Р\.?\s*[-–—]\s*\d{2}(?:[.,]\d+)?\s*СМ",
            raw,
        )
        if match:
            size = int(match.group(1))
            return {size} if 30 <= size <= 70 else None

        # RU-размер обуви и длина стельки без СМ.
        match = re.fullmatch(
            r"(\d{2})\s*[-–—]\s*(\d{2}(?:[.,]\d+)?)",
            raw,
        )
        if match:
            size = int(match.group(1))
            insole = float(match.group(2).replace(",", "."))
            if 35 <= size <= 47 and 20 <= insole <= 33:
                return {size}

        # Диапазон размеров одежды через слеш.
        match = re.fullmatch(r"(\d{2})\s*/\s*(\d{2})", raw)
        if match:
            low, high = map(int, match.groups())
            if 36 <= low <= high <= 70 and high - low <= 8:
                return set(range(low, high + 1, 2))

        # Размер обуви + длина стопы.
        raw = re.sub(
            r"\s*[-–—]\s*\d{2}[.,]\d+\s*СМ$",
            "",
            raw,
        )

        single = re.fullmatch(r"(\d{2})", raw)

        if single:
            value = int(single.group(1))
            return {value} if 30 <= value <= 70 else None

        pair = re.fullmatch(
            r"(\d{2})\s*[-–—]\s*(\d{2})",
            raw,
        )

        if pair:
            low, high = map(int, pair.groups())

            if 30 <= low <= high <= 70 and high - low <= 8:
                return set(range(low, high + 1, 2))

        return None

    @classmethod
    def select_available_size(
        cls,
        recommended: str | None,
        available_sizes: list[str] | None,
    ) -> str | None:
        """
        Возвращает исходную метку продавца,
        только если совпадение подтверждено.
        """
        target = cls.size_numbers(recommended)

        if not target or not available_sizes:
            return None

        for label in available_sizes:
            values = cls.size_numbers(label)

            if values and target & values:
                return str(label)

        return None

    @classmethod
    def recommend_for_offer(
        cls,
        available_sizes: list[str] | None,
        category: str | None,
        gender: str | None,
        chest: float | None,
        waist: float | None,
        hips: float | None,
        shoe_size: float | None = None,
    ) -> str | None:
        """
        Единый расчёт для любого маркетплейса.

        Для одежды используем размерную модель.
        Для обуви — размер ноги из анкеты.
        """
        sizes = cls.normalize_available_sizes(
            available_sizes, category
        )

        if not sizes:
            return None

        normalized_category = (category or "").lower()

        if normalized_category in {
            "shoes", "shoe", "footwear", "обувь"
        }:
            if shoe_size is None:
                return None

            return cls.select_available_size(
                str(shoe_size).removesuffix(".0"),
                sizes,
            )

        if normalized_category in {
            "accessory", "accessories", "аксессуары"
        }:
            return None

        # Определяем целевой RU-размер независимо
        # от ассортимента конкретного продавца.
        target = cls.recommend_size(
            available_sizes=[
                str(number) for number in range(36, 72, 2)
            ],
            category=normalized_category,
            gender=gender,
            chest=chest,
            waist=waist,
            hips=hips,
        )

        return cls.select_available_size(target, sizes)

    @staticmethod
    def normalize_available_sizes(
        sizes: list[Any] | None,
        category: str | None = None,
    ) -> list[str]:
        """
        Преобразует размеры маркетплейса в список строк.

        Например:
        [{"name": "42"}, {"name": "44"}] -> ["42", "44"]

        Для аксессуаров размерный ряд не показываем.
        """
        if category == "accessory":
            return []

        if not sizes:
            return []

        result: list[str] = []

        for item in sizes:
            value: Any = None

            if isinstance(item, dict):
                value = item.get("name") or item.get("orig_name") or item.get("origName")
            elif isinstance(item, (str, int, float)):
                value = item

            if value is None:
                continue

            value = str(value).strip()

            if value and value not in result:
                result.append(value)

        return result

    @staticmethod
    def recommend_size(
        available_sizes: list[str],
        category: str | None,
        gender: str | None,
        chest: float | None,
        waist: float | None,
        hips: float | None,
    ) -> str | None:
        """
        Рассчитывает базовый RU-размер и выбирает ближайший
        реально доступный размер продавца.

        Для обуви без длины стопы и для аксессуаров
        рекомендацию не формируем.
        """
        if category in {"accessory", "shoes"}:
            return None

        if not available_sizes or not gender:
            return None

        # Поддерживаем как одиночные RU-размеры ("44"),
        # так и диапазоны продавца ("44-46").
        #
        # Храним исходную строку размера, потому что именно её нужно
        # вернуть frontend для предвыбора из available_sizes.
        size_options: list[tuple[str, int, int]] = []

        for value in available_sizes:
            raw = str(value).strip()

            if not raw:
                continue

            # Универсальный разбор размера.
            values = SizeRecommendationService.size_numbers(raw)
            if values:
                size_options.append((raw, min(values), max(values)))
                continue

            # Обычный размер: "44"
            try:
                size = int(raw)
            except ValueError:
                size = None

            if size is not None:
                if 36 <= size <= 70:
                    size_options.append((raw, size, size))
                continue

            # Диапазон: "40-42", "44–46", "48—50"
            normalized = (
                raw.replace("–", "-")
                .replace("—", "-")
                .replace("−", "-")
            )

            parts = [part.strip() for part in normalized.split("-", 1)]

            if len(parts) != 2:
                continue

            try:
                start = int(parts[0])
                end = int(parts[1])
            except ValueError:
                continue

            if start > end:
                start, end = end, start

            if 36 <= start <= 70 and 36 <= end <= 70:
                size_options.append((raw, start, end))

        if not size_options:
            return None

        # Базовый RU-размер.
        #
        # Обхват груди даёт наиболее универсальную отправную точку:
        # RU размер ≈ chest / 2.
        #
        # Для нижней части одежды дополнительно учитываем бёдра.
        target_size: float | None = None

        if category == "bottom":
            candidates = []

            if waist is not None:
                # Приближённое соответствие для fallback.
                candidates.append((waist + 16) / 2)

            if hips is not None:
                candidates.append((hips - 8) / 2)

            if candidates:
                target_size = max(candidates)

        else:
            if chest is not None:
                target_size = chest / 2

            if category == "dress" and hips is not None:
                hips_size = (hips - 8) / 2
                target_size = max(
                    target_size or hips_size,
                    hips_size,
                )

        if target_size is None:
            return None

        # RU размеры обычно идут с шагом 2.
        target_ru = int(round(target_size / 2) * 2)

        # Сначала ищем размер или диапазон, содержащий target_ru.
        containing = [
            option
            for option in size_options
            if option[1] <= target_ru <= option[2]
        ]

        if containing:
            recommended = min(
                containing,
                key=lambda option: (
                    option[2] - option[1],
                    option[1],
                ),
            )
            return recommended[0]

        # STYLELINK_STRICT_SIZE_V1
        # Если рассчитанный RU-размер не входит ни в один
        # доступный диапазон, не подменяем его ближайшим.
        #
        # Например, при target_ru=50 и размерах ["42", "44"]
        # нельзя рекомендовать "44".
        return None
