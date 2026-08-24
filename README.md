# AI·StyleLink FastAPI Backend

MVP backend: FastAPI + PostgreSQL + SQLAlchemy 2 + Alembic + JWT.

## Start

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

docker compose up -d

alembic revision --autogenerate -m "initial schema"
alembic upgrade head

uvicorn app.main:app --reload

Open http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/health

## API

POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/users/me
POST /api/v1/wardrobe
GET  /api/v1/wardrobe
POST /api/v1/outfits
GET  /api/v1/outfits

PostgreSQL host port: 5433
