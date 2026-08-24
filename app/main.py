from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.api.v1.router import api_router
from app.core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(title="AI·StyleLink API", version="1.0.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["system"])
async def health():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": result.scalar()}
