from typing import Any, AsyncIterator, Protocol


class EventsProviderClient(Protocol):
    """Интерфейс для взаимодействия с внешним провайдером событий."""

    async def iter_pages(
        self, changed_at: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """
        Итерировать страницы событий от провайдера (cursor-пагинация).

        Args:
            changed_at: ISO-строка даты. Если передана — возвращает только события,
                изменённые после этой метки. При первой синхронизации передаётся
                "2000-01-01" для получения всех событий.

        Yields:
            Список событий на текущей странице.
        """
        ...

    async def get_seats(self, event_id: str) -> list[str]:
        """
        Получить список доступных мест для события.

        Args:
            event_id: Строковый UUID события.

        Returns:
            Список идентификаторов мест, например ``["A1", "A3", "B5"]``.
        """
        ...

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        """
        Зарегистрировать участника на событие.

        Args:
            event_id: UUID события.
            first_name: Имя участника.
            last_name: Фамилия участника.
            email: Email участника.
            seat: Номер места.

        Returns:
            ticket_id, выданный провайдером.
        """
        ...

    async def unregister(self, event_id: str, ticket_id: str) -> None:
        """
        Отменить регистрацию участника.

        Args:
            event_id: UUID события.
            ticket_id: Идентификатор билета, выданный провайдером.
        """
        ...
