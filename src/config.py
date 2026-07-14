from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str = "changeme"
    telegram_webhook_secret: str = "changeme"
    telegram_mode: str = "polling"

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"

    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "prompt-payloads"
    minio_secure: bool = False

    prompt_retention_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
