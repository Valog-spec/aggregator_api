"""Конфигурация приложения через переменные окружения."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env файла или переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/aggregator"
    REDIS_URL: str = "redis://localhost:6379/0"
    EVENTS_PROVIDER_BASE_URL: str = "https://events-provider.dev-2.python-labs.ru"
    EVENTS_PROVIDER_API_KEY: str = "your-key-here"


settings = Settings()
