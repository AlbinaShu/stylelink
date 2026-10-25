from typing import Any


class SizeRecommendationService:
    """Backend-логика работы с размерным рядом продавца."""

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

        # Если target_ru не входит ни в один доступный диапазон,
        # выбираем ближайший размер или диапазон продавца.
        def distance(option: tuple[str, int, int]) -> tuple[int, int]:
            _, start, end = option

            if target_ru < start:
                return (start - target_ru, start)

            return (target_ru - end, start)

        recommended = min(size_options, key=distance)

        # Возвращаем исходное значение из available_sizes:
        # например "44" или "44-46".
        return recommended[0]
