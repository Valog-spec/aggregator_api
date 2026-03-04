import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.models.event import EventStatus
from src.use_cases.events_use_cases import GetEventDetailUseCase, GetSeatsUseCase
from tests.fakes import InMemoryTTLCache


def make_event(status: EventStatus = EventStatus.published) -> MagicMock:
    """Фабрика мок-объекта Event с подгруженной площадкой."""
    event = MagicMock()
    event.id = uuid.uuid4()
    event.name = "Test Event"
    event.status = status
    event.event_time = "2026-01-11T17:00:00+03:00"
    event.registration_deadline = None
    event.number_of_visitors = 5
    event.place = MagicMock()
    event.place.id = uuid.uuid4()
    event.place.name = "Test Place"
    event.place.city = "Moscow"
    event.place.address = "Test St 1"
    event.place.seats_pattern = None
    return event


@pytest.mark.anyio
async def test_get_event_detail_not_found():
    """Возвращает 404, если событие не найдено в БД."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    use_case = GetEventDetailUseCase(repo)

    with pytest.raises(HTTPException) as exc_info:
        await use_case.execute(uuid.uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_get_event_detail_found():
    """Возвращает EventDetail, если событие найдено."""
    event = make_event()
    repo = AsyncMock()
    repo.get_by_id.return_value = event

    use_case = GetEventDetailUseCase(repo)
    result = await use_case.execute(event.id)

    assert result.name == event.name
    repo.get_by_id.assert_called_once_with(event.id)


@pytest.mark.anyio
async def test_get_seats_cache_hit_skips_provider():
    """При попадании в кеш провайдер не вызывается."""
    event_id = uuid.uuid4()
    cache = InMemoryTTLCache()
    await cache.set(str(event_id), ["A1", "A2", "A3"])

    provider = AsyncMock()
    use_case = GetSeatsUseCase(provider, cache)

    result = await use_case.execute(event_id)

    assert result.available_seats == ["A1", "A2", "A3"]
    provider.get_seats.assert_not_called()


@pytest.mark.anyio
async def test_get_seats_cache_miss_calls_provider():
    """При промахе кеша — идём к провайдеру и кешируем результат."""
    event_id = uuid.uuid4()
    cache = InMemoryTTLCache()

    provider = AsyncMock()
    provider.get_seats.return_value = ["B1", "B2"]

    use_case = GetSeatsUseCase(provider, cache)
    result = await use_case.execute(event_id)

    assert result.available_seats == ["B1", "B2"]
    provider.get_seats.assert_called_once_with(str(event_id))

    # Убеждаемся что результат закешировался
    cached = await cache.get(str(event_id))
    assert cached == ["B1", "B2"]


@pytest.mark.anyio
async def test_get_seats_second_call_uses_cache():
    """Второй вызов берёт данные из кеша, провайдер вызывается только раз."""
    event_id = uuid.uuid4()
    cache = InMemoryTTLCache()

    provider = AsyncMock()
    provider.get_seats.return_value = ["C1"]

    use_case = GetSeatsUseCase(provider, cache)
    await use_case.execute(event_id)
    await use_case.execute(event_id)

    assert provider.get_seats.call_count == 1
