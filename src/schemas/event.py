import uuid
from datetime import datetime

from pydantic import BaseModel

from src.models.event import EventStatus


class PlaceBase(BaseModel):
    """Базовая схема площадки (без схемы мест)."""

    id: uuid.UUID
    name: str
    city: str
    address: str

    model_config = {"from_attributes": True}


class PlaceWithPattern(PlaceBase):
    """Схема площадки с полем схемы расположения мест."""

    seats_pattern: str | None = None


class EventListItem(BaseModel):
    """Краткая схема события для отображения в списке."""

    id: uuid.UUID
    name: str
    place: PlaceBase
    event_time: datetime
    registration_deadline: datetime | None = None
    status: EventStatus
    number_of_visitors: int | None = None

    model_config = {"from_attributes": True}


class EventDetail(BaseModel):
    """Детальная схема события с полной информацией о площадке."""

    id: uuid.UUID
    name: str
    place: PlaceWithPattern
    event_time: datetime
    registration_deadline: datetime | None = None
    status: EventStatus
    number_of_visitors: int | None = None

    model_config = {"from_attributes": True}


class PaginatedEvents(BaseModel):
    """Постраничный ответ со списком событий в DRF-стиле."""

    count: int
    next: str | None
    previous: str | None
    results: list[EventListItem]


class SeatsResponse(BaseModel):
    """Ответ с доступными местами для события."""

    event_id: uuid.UUID
    available_seats: list[str]
