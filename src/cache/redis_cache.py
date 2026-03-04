import json
from typing import Any

import redis.asyncio as aioredis

from src.configs.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


class RedisTTLCache:
    """Асинхронный кеш на базе Redis с автоматическим TTL."""

    def __init__(self, client: aioredis.Redis, ttl: int = 30, prefix: str = "") -> None:
        """
        Args:
            client: Инстанс Redis-клиента.
            ttl: Время жизни записи в секундах.
            prefix: Префикс ключей для изоляции namespace.
        """
        self._client = client
        self._ttl = ttl
        self._prefix = prefix

    def _key(self, key: str) -> str:
        """Построить полный ключ с префиксом."""
        return f"{self._prefix}:{key}" if self._prefix else key

    async def get(self, key: str) -> Any | None:
        """Получить значение из Redis.

        Args:
            key: Ключ кеша (без префикса).

        Returns:
            Десериализованное значение или ``None`` при промахе / истёкшем TTL.
        """
        raw = await self._client.get(self._key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any) -> None:
        """Сохранить значение в Redis с TTL.

        Args:
            key: Ключ кеша (без префикса).
            value: JSON-совместимое значение.
        """
        await self._client.setex(self._key(key), self._ttl, json.dumps(value))

    async def delete(self, key: str) -> None:
        """Удалить одну запись из Redis.

        Args:
            key: Ключ кеша (без префикса).
        """
        await self._client.delete(self._key(key))

    async def delete_many(self, keys: list[str]) -> None:
        """Удалить несколько записей за один round-trip (инвалидация).

        Args:
            keys: Список ключей без префикса. Пустой список — no-op.
        """
        if not keys:
            return
        await self._client.delete(*[self._key(k) for k in keys])


def get_seats_cache() -> RedisTTLCache:
    """Создать экземпляр кеша мест с префиксом ``seats`` и TTL 30 секунд."""
    return RedisTTLCache(client=redis_client, ttl=30, prefix="seats")
