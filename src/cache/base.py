from typing import Any, Protocol


class AsyncCacheProtocol(Protocol):
    """Интерфейс асинхронного кеша «ключ → значение».

    Реализуется как Redis-кешем, так и InMemory-кешем (для тестов).
    """

    async def get(self, key: str) -> Any | None:
        """Получить значение по ключу. Возвращает ``None`` при промахе или истечении TTL."""
        ...

    async def set(self, key: str, value: Any) -> None:
        """Сохранить значение с TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Удалить запись по ключу."""
        ...

    async def delete_many(self, keys: list[str]) -> None:
        """Удалить несколько записей за один вызов (инвалидация)."""
        ...
