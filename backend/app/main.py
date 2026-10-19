import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.database import engine
from app.services.survey_scheduler import survey_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(
        survey_scheduler()
    )

    try:
        yield
    finally:
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await engine.dispose()


app = FastAPI(
    title="AI·StyleLink API",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_persist_authorization=True,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": result.scalar(),
        }