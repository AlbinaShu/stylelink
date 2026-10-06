import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.fashion_clip import (
    FashionClipRequest,
    FashionClipResponse,
)


class FashionClipError(RuntimeError):
    """Ошибка взаимодействия с FashionCLIP service."""


class FashionClipClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (
            base_url or settings.fashion_clip_url
        ).rstrip("/")

        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.fashion_clip_timeout_seconds
        )

    async def create_outfits(
        self,
        request: FashionClipRequest,
    ) -> FashionClipResponse:
        url = f"{self.base_url}/api/v1/outfits"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                response = await client.post(
                    url,
                    json=request.model_dump(
                        mode="json",
                        exclude_none=True,
                    ),
                )

        except httpx.TimeoutException as exc:
            raise FashionClipError(
                "FashionCLIP request timed out"
            ) from exc

        except httpx.RequestError as exc:
            raise FashionClipError(
                f"FashionCLIP connection error: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise FashionClipError(
                "FashionCLIP returned "
                f"HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )

        try:
            return FashionClipResponse.model_validate(
                response.json()
            )

        except (ValueError, ValidationError) as exc:
            raise FashionClipError(
                "FashionCLIP returned invalid response"
            ) from exc
