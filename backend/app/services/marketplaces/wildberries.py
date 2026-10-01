import asyncio
import json
from typing import Any
from urllib.parse import urlencode

from app.services.marketplaces.base import MarketplaceService


class WildberriesMarketplace(MarketplaceService):
    SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v18/search"

    USER_AGENT = "Mozilla/5.0"

    def _basket_card_url(self, nm_id: int, shard: int) -> str:
        vol = nm_id // 100000
        part = nm_id // 1000
        host = f"{shard:02d}" if shard < 10 else str(shard)

        return (
            f"https://basket-{host}.wbbasket.ru/"
            f"vol{vol}/part{part}/{nm_id}/info/ru/card.json"
        )

    def _image_url(self, nm_id: int, shard: int, index: int = 1) -> str:
        vol = nm_id // 100000
        part = nm_id // 1000
        host = f"{shard:02d}" if shard < 10 else str(shard)

        return (
            f"https://basket-{host}.wbbasket.ru/"
            f"vol{vol}/part{part}/{nm_id}/images/big/{index}.webp"
        )

    async def _find_basket_shard(
        self,
        nm_id: int,
        max_shard: int = 50,
    ) -> int | None:
        for shard in range(1, max_shard + 1):
            try:
                await self._get_json(
                    self._basket_card_url(nm_id, shard),
                    timeout=4,
                    attempts=1,
                )
            except RuntimeError:
                continue

            return shard

        return None

    async def search_products(
        self,
        search_query: str,
        page: int = 1,
    ) -> list[dict]:
        params = {
            "appType": 1,
            "curr": "rub",
            "dest": -1257786,
            "lang": "ru",
            "page": page,
            "query": search_query,
            "resultset": "catalog",
            "sort": "popular",
            "spp": 30,
            "suppressSpellcheck": "false",
        }

        url = f"{self.SEARCH_URL}?{urlencode(params)}"

        data = await self._get_json(url)

        products = data.get("products") or []

        semaphore = asyncio.Semaphore(10)

        async def normalize_product(product: dict[str, Any]) -> dict:
            async with semaphore:
                return await self._normalize_product(product)

        return await asyncio.gather(
            *(normalize_product(product) for product in products)
        )

    async def _get_json(
        self,
        url: str,
        timeout: int = 15,
        attempts: int = 3,
    ) -> dict[str, Any]:
        last_error = "unknown error"

        for attempt in range(1, attempts + 1):
            process = await asyncio.create_subprocess_exec(
                "curl",
                "-sS",
                "--compressed",
                "--max-time",
                str(timeout),
                "-A",
                self.USER_AGENT,
                "-H",
                "Accept: application/json",
                "-w",
                "\n%{http_code}",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace").strip()

            if "\n" not in output:
                last_error = error_output or "Wildberries returned invalid response"
            else:
                body, status = output.rsplit("\n", 1)
                status = status.strip()

                if process.returncode == 0 and status == "200":
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError as exc:
                        last_error = f"Wildberries returned invalid JSON: {exc}"
                    else:
                        if isinstance(data, dict):
                            return data

                        last_error = "Wildberries returned unexpected JSON"

                elif status == "429":
                    last_error = "Wildberries rate limit (429)"

                elif status == "403":
                    last_error = "Wildberries access denied (403)"

                else:
                    last_error = (
                        error_output
                        or f"Wildberries HTTP {status or 'unknown'}"
                    )

            if attempt < attempts:
                await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(
            f"Wildberries request failed after {attempts} attempts: {last_error}"
        )

    async def _normalize_product(self, product: dict[str, Any]) -> dict:
        sizes = product.get("sizes") or []

        normalized_sizes = []

        for size in sizes:
            price = size.get("price") or {}

            normalized_sizes.append(
                {
                    "name": size.get("name"),
                    "orig_name": size.get("origName"),
                    "option_id": size.get("optionId"),
                    "price": {
                        "basic": price.get("basic"),
                        "product": price.get("product"),
                        "logistics": price.get("logistics"),
                        "return": price.get("return"),
                        "cashback": price.get("cashback"),
                    },
                }
            )

        prices = [
            size["price"]["product"]
            for size in normalized_sizes
            if size["price"]["product"] is not None
        ]

        price = min(prices) / 100 if prices else None

        colors = [
            {
                "name": color.get("name"),
                "id": color.get("id"),
            }
            for color in (product.get("colors") or [])
        ]

        external_id = product.get("id")

        image_url = None

        if external_id:
            shard = await self._find_basket_shard(external_id)

            if shard is not None:
                image_url = self._image_url(
                    external_id,
                    shard,
                    index=1,
                )

        return {
            "marketplace": "wildberries",
            "external_id": external_id,
            "image_url": image_url,
            "product_url": (
                f"https://www.wildberries.ru/catalog/{external_id}/detail.aspx"
                if external_id
                else None
            ),
            "imt_id": product.get("root"),
            "name": product.get("name"),
            "brand": product.get("brand"),
            "supplier": product.get("supplier"),
            "supplier_id": product.get("supplierId"),
            "rating": product.get("rating"),
            "review_rating": product.get("reviewRating"),
            "feedbacks": product.get("feedbacks"),
            "subject_id": product.get("subjectId"),
            "subject_parent_id": product.get("subjectParentId"),
            "price": price,
            "colors": colors,
            "sizes": normalized_sizes,
            "raw_data": product,
        }
