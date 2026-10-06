import httpx

from app.core.config import settings
from app.schemas.size_shift import (
    SizeShiftRequest,
    SizeShiftResponse,
)


class SizeShiftError(Exception):
    pass


class SizeShiftClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (
            base_url or settings.size_shift_url
        ).rstrip("/")

        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.size_shift_timeout_seconds
        )

    async def predict(
        self,
        request: SizeShiftRequest,
    ) -> SizeShiftResponse:
        url = f"{self.base_url}/v1/size-shift/predict"

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
            raise SizeShiftError(
                "Size Shift ML request timed out"
            ) from exc

        except httpx.RequestError as exc:
            raise SizeShiftError(
                f"Size Shift ML request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise SizeShiftError(
                "Size Shift ML returned "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        try:
            return SizeShiftResponse.model_validate(
                response.json()
            )
        except Exception as exc:
            raise SizeShiftError(
                "Invalid Size Shift ML response"
            ) from exc
