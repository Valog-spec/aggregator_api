import uuid
from datetime import datetime

import httpx
from fastapi import HTTPException

from src.cache.base import AsyncCacheProtocol
from src.clients.base import EventsProviderClient
from src.models.event import EventStatus
from src.repositories.event_repository import EventRepository
from src.schemas.event import EventDetail, EventListItem, SeatsResponse


class GetEventsUseCase:
    """Получение постраничного списка событий с фильтрацией."""

    def __init__(self, event_repo: EventRepository) -> None:
        self._repo = event_repo

    async def execute(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: datetime | None = None,
        status: EventStatus | None = None,
    ) -> tuple[list[EventListItem], int]:
        """Вернуть страницу событий.

        Args:
            page: Номер страницы (начиная с 1).
            page_size: Количество элементов на странице.
            date_from: Фильтр — события начиная с этой даты (необязательно).
            status: Фильтр по статусу (необязательно).

        Returns:
            Кортеж (список элементов, общее количество записей).
        """
        events, total = await self._repo.get_paginated(
            page=page, page_size=page_size, date_from=date_from, status=status
        )
        items = [EventListItem.model_validate(e) for e in events]
        return items, total


class GetEventDetailUseCase:
    """Получение детальной информации о событии по ID."""

    def __init__(self, event_repo: EventRepository) -> None:
        self._repo = event_repo

    async def execute(self, event_id: uuid.UUID) -> EventDetail:
        """Найти событие по идентификатору.

        Args:
            event_id: UUID события.

        Returns:
            Детальная схема события вместе с данными площадки.

        Raises:
            HTTPException: 404, если событие не найдено.
        """
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        return EventDetail.model_validate(event)


class GetSeatsUseCase:
    """Получение доступных мест для события по паттерну cache-aside.

    Cache-aside:
        1. Читаем из кеша.
        2. Если промах — идём к провайдеру, кладём результат в кеш.
        3. Возвращаем данные.
    """

    def __init__(
        self, provider_client: EventsProviderClient, cache: AsyncCacheProtocol
    ) -> None:
        self._client = provider_client
        self._cache = cache

    async def execute(self, event_id: uuid.UUID) -> SeatsResponse:
        """Вернуть список доступных мест (cache-aside, TTL 30 секунд).

        Args:
            event_id: UUID события.

        Returns:
            Ответ со списком мест от провайдера или из кеша.
        """
        cache_key = str(event_id)

        cached = await self._cache.get(cache_key)
        if cached is not None:
            return SeatsResponse(event_id=event_id, available_seats=cached)

        try:
            seats = await self._client.get_seats(cache_key)
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get(
                    "detail", "Ошибка получения мест у провайдера"
                )
            except Exception:
                detail = "Ошибка получения мест у провайдера"
            raise HTTPException(
                status_code=exc.response.status_code, detail=detail
            ) from exc
        await self._cache.set(cache_key, seats)
        return SeatsResponse(event_id=event_id, available_seats=seats)
