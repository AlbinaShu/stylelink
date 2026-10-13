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

        # Пока рекомендуем только для размеров RU вида 40, 42, 44...
        numeric_sizes: list[int] = []

        for value in available_sizes:
            try:
                size = int(value)
            except (TypeError, ValueError):
                continue

            if 36 <= size <= 70:
                numeric_sizes.append(size)

        if not numeric_sizes:
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

        # Выбираем ближайший реально доступный размер продавца.
        recommended = min(
            numeric_sizes,
            key=lambda size: (abs(size - target_ru), size),
        )

        return str(recommended)
