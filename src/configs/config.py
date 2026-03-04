"""Конфигурация приложения через переменные окружения."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env файла или переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str
    REDIS_URL: str | None
    EVENTS_PROVIDER_BASE_URL: str
    EVENTS_PROVIDER_API_KEY: str

    POSTGRES_CONNECTION_STRING: str | None = None

    @model_validator(mode="after")
    def apply_postgres_connection_string(self) -> "Settings":
        """Использовать POSTGRES_CONNECTION_STRING из кластера если задан."""
        if self.POSTGRES_CONNECTION_STRING:
            self.DATABASE_URL = self.POSTGRES_CONNECTION_STRING.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )
        return self


settings = Settings()
