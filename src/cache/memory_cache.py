import time
from typing import Any


class InMemoryTTLCache:
    """Асинхронный in-memory кэш с автоматическим TTL.

    Реализует тот же интерфейс ``AsyncCacheProtocol``, что и ``RedisTTLCache``.
    Используется когда Redis недоступен.
    """

    def __init__(self, ttl: float = 30.0) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self._store.pop(key, None)
