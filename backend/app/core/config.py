from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI·StyleLink API"
    app_env: str = "development"
    debug: bool = True
    database_url: str
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str
    smtp_password: str
    smtp_from: str
    gigachat_credentials: str
    gigachat_model: str

    # Pilot defaults preserve the legacy source; enable paid providers explicitly.
    catalog_provider: Literal["yandex_market", "bhapi_wb"] = "yandex_market"
    reviews_provider: Literal["yandex_market", "mpdown", "apify", "none"] = "yandex_market"
    bhapi_wb_token: SecretStr = SecretStr("")
    mpdown_api_key: SecretStr = SecretStr("")
    apify_api_token: SecretStr = SecretStr("")
    apify_run_cap_usd: float = Field(default=0.15, gt=0, le=1)
    apify_generation_cap_usd: float = Field(default=1.0, gt=0, le=5)
    apify_reviews_timeout_seconds: float = Field(default=90, gt=0, le=180)
    apify_allow_group_reviews: bool = False
    wb_pickup_point_id: int | None = Field(default=None, gt=0)
    marketplace_search_limit: int = Field(default=20, ge=1, le=30)
    marketplace_max_calls: int = Field(default=150, ge=1, le=500)
    marketplace_max_searches: int = Field(default=6, ge=1, le=6)
    marketplace_timeout_seconds: float = Field(default=120, gt=0, le=240)
    marketplace_review_limit: int = Field(default=20, ge=1, le=20)
    marketplace_review_max_pages: int = Field(default=2, ge=1, le=10)
    outfit_count: int = Field(default=5, ge=1, le=5)

    # FashionCLIP ML service
    fashion_clip_url: str = "http://127.0.0.1:8001"
    fashion_clip_timeout_seconds: float = 60.0

    size_shift_url: str = "http://127.0.0.1:8002"
    size_shift_timeout_seconds: float = 60.0

    survey_test_mode: bool = False
    survey_test_period_minutes: int = 10
    survey_period_days: int = 14
    survey_test_email_delay_minutes: int = 15
    survey_email_delay_days: int = 5
    survey_token_lifetime_days: int = 14

    survey_frontend_url: str = "http://localhost:3000/survey"
    survey_reminder_delay_days: int = 3
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
