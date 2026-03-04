import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.event import Event, EventStatus
from src.models.place import Place

logger = logging.getLogger(__name__)


def _parse_dt(value: str | datetime | None) -> datetime | None:
    """Привести значение к datetime. Принимает ISO-строку или уже datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        logger.warning("Не удалось распарсить datetime: %r", value)
        return None


class EventRepository:
    """Доступ к данным событий и площадок в БД."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Args:
            session: Активная асинхронная сессия SQLAlchemy.
        """
        self._session = session

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: datetime | None = None,
        status: EventStatus | None = None,
    ) -> tuple[list[Event], int]:
        """
        Получить страницу событий с фильтрацией.

        Args:
            page: Номер страницы (начиная с 1).
            page_size: Количество записей на странице.
            date_from: Фильтр — события начиная с этой даты (необязательно).
            status: Фильтр по статусу события (необязательно).

        Returns:
            Кортеж (список событий, общее количество записей).
        """
        query = select(Event).options(selectinload(Event.place))

        if date_from:
            query = query.where(Event.event_time >= date_from)
        if status:
            query = query.where(Event.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total: int = (await self._session.execute(count_query)).scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        events = list(result.scalars().all())
        return events, total

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        """
        Найти событие по UUID с подгрузкой площадки.

        Args:
            event_id: UUID события.

        Returns:
            Объект события или None, если не найдено.
        """
        result = await self._session.execute(
            select(Event).options(selectinload(Event.place)).where(Event.id == event_id)
        )
        return result.scalar_one_or_none()

    async def upsert_from_provider(self, provider_event: dict[str, Any]) -> Event:
        """
        Создать или обновить площадку и событие по данным из провайдера.

        Args:
            provider_event: Словарь с данными события от провайдера.
                Ожидаются ключи: id, name, event_time,
                registration_deadline, place, status,
                number_of_visitors.

        Returns:
            Созданный или обновлённый объект события.
        """
        place_data = provider_event.get("place", {})
        try:
            place_id = (
                uuid.UUID(place_data["id"]) if "id" in place_data else uuid.uuid4()
            )
        except (ValueError, KeyError):
            logger.warning(
                "Невалидный place.id от провайдера: %r", place_data.get("id")
            )
            place_id = uuid.uuid4()

        existing_place = await self._session.get(Place, place_id)
        if existing_place is None:
            place = Place(
                id=place_id,
                name=place_data.get("name", ""),
                city=place_data.get("city", ""),
                address=place_data.get("address", ""),
                seats_pattern=place_data.get("seats_pattern"),
            )
            self._session.add(place)
        else:
            existing_place.name = place_data.get("name", existing_place.name)
            existing_place.city = place_data.get("city", existing_place.city)
            existing_place.address = place_data.get("address", existing_place.address)
            existing_place.seats_pattern = place_data.get(
                "seats_pattern", existing_place.seats_pattern
            )

        try:
            event_id = uuid.UUID(provider_event["id"])
        except (ValueError, KeyError) as exc:
            raise ValueError(
                f"Невалидный event.id от провайдера: {provider_event.get('id')!r}"
            ) from exc
        existing_event = await self._session.get(Event, event_id)

        status_raw = provider_event.get("status", "new")
        try:
            status = EventStatus(status_raw)
        except ValueError:
            status = EventStatus.new

        if existing_event is None:
            event = Event(
                id=event_id,
                name=provider_event.get("name", ""),
                event_time=_parse_dt(provider_event["event_time"]),
                registration_deadline=_parse_dt(
                    provider_event.get("registration_deadline")
                ),
                place_id=place_id,
                status=status,
                number_of_visitors=provider_event.get("number_of_visitors"),
            )
            self._session.add(event)
        else:
            existing_event.name = provider_event.get("name", existing_event.name)
            existing_event.event_time = (
                _parse_dt(provider_event.get("event_time")) or existing_event.event_time
            )
            existing_event.registration_deadline = (
                _parse_dt(provider_event.get("registration_deadline"))
                or existing_event.registration_deadline
            )
            existing_event.place_id = place_id
            existing_event.status = status
            existing_event.number_of_visitors = provider_event.get(
                "number_of_visitors", existing_event.number_of_visitors
            )
            event = existing_event

        await self._session.flush()
        return event

    async def commit(self) -> None:
        """Зафиксировать текущую транзакцию."""
        await self._session.commit()
