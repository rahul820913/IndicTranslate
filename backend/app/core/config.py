from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    redis_url: str | None = None
    secret_key: str = "change-me-in-production"
    access_token_minutes: int = 60 * 24

    translator_backend: str = "indictrans2"  # "mock" | "indictrans2"
    device: str = "auto"  # auto | cpu | cuda
    model_en_indic: str = "ai4bharat/indictrans2-en-indic-dist-200M"
    model_indic_en: str = "ai4bharat/indictrans2-indic-en-dist-200M"
    model_version: str = "baseline-v1"

    max_chars: int = 2000
    rate_limit_per_minute: int = 30
    cache_ttl_seconds: int = 60 * 60 * 24
    cors_origins: str = "http://localhost:5173"


settings = Settings()
