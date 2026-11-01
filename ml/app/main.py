import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.model_runtime import get_fit_model, get_outfit_models, preload_models
from app.outfits import create_outfits
from app.schemas import OutfitRequest, OutfitResponse, SizeShiftRequest, SizeShiftResponse
from app.size_shift import predict_size_shift


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("ML_PRELOAD", "1") == "1":
        await asyncio.to_thread(preload_models)
    yield


app = FastAPI(title="AI StyleLink ML API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    ready = bool(get_outfit_models.cache_info().currsize and get_fit_model.cache_info().currsize)
    fit_backend = (
        getattr(get_fit_model(), "backend", "unknown") if ready else os.getenv("FIT_MODEL_BACKEND", "b2")
    )
    return {
        "status": "ok" if ready else "loading",
        "mode": "pretrained",
        "fit_backend": fit_backend,
    }


@app.post("/api/v1/outfits", response_model=OutfitResponse)
def outfits(request: OutfitRequest) -> OutfitResponse:
    return create_outfits(request)


@app.post("/v1/size-shift/predict", response_model=SizeShiftResponse)
def size_shift(request: SizeShiftRequest) -> SizeShiftResponse:
    return predict_size_shift(request)
