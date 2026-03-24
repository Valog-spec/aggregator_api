import asyncio
import time
from collections import OrderedDict
from typing import List, Optional, Tuple


class LruCache:
    def __init__(self, max_size: int = 10):
        self._max_size = max_size
        self._cache: OrderedDict[str, Tuple[str, Optional[float]]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str):
        """
        Получить значение по ключу.
        Обновляет порядок в LRU при успешном получении.

        Returns:
            Значение или None если ключ не найден или TTL истек
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            value, expires_at = entry

            if expires_at is not None and time.monotonic() > expires_at:
                del self._cache[key]
                return None

            self._cache.move_to_end(key)

            return value

    async def put(self, key: str, value: str, ttl_seconds: int = 0) -> None:
        """
        Добавить или обновить значение.
        Обновляет порядок в LRU.

        Args:
            key: Ключ
            value: Значение
            ttl_seconds: TTL в секундах. 0 = без TTL.
        """
        async with self._lock:
            if ttl_seconds == 0:
                expires_at = None
            else:
                expires_at = time.monotonic() + ttl_seconds
            if key in self._cache:
                del self._cache[key]

            self._cache[key] = (value, expires_at)

            while len(self._cache) > self._max_size:
                old_key, _ = self._cache.popitem(last=False)

    async def delete(self, key: str) -> bool:
        """
        Удалить ключ.

        Returns:
            True если ключ был удален, False если не существовал
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def list_by_prefix(self, prefix: str) -> List[Tuple[str, str]]:
        """
        Получить все ключи и значения с указанным префиксом.
        Истекшие ключи не возвращаются и удаляются.

        Returns:
            Список кортежей (key, value)
        """
        async with self._lock:
            result = []
            current_time = time.monotonic()
            expired_keys = []

            for key, (value, expires_at) in self._cache.items():
                if expires_at is not None and current_time > expires_at:
                    expired_keys.append(key)
                    continue

                if key.startswith(prefix):
                    result.append((key, value))
            for key in expired_keys:
                del self._cache[key]
            return result
