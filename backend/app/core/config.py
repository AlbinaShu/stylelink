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
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_from: str
    gigachat_credentials: str
    gigachat_model: str

    # FashionCLIP ML service
    fashion_clip_url: str = "http://127.0.0.1:8001"
    fashion_clip_timeout_seconds: float = 60.0

    size_shift_url: str = "http://127.0.0.1:8002"
    size_shift_timeout_seconds: float = 60.0
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()