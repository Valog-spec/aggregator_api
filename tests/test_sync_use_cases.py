from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.sync_meta import SyncStatus
from src.use_cases.sync_use_cases import SyncEventsUseCase
from tests.fakes import InMemoryTTLCache


def make_meta(last_changed_at: datetime | None = None) -> MagicMock:
    """Фабрика мок-объекта SyncMeta."""
    meta = MagicMock()
    meta.last_changed_at = last_changed_at
    meta.sync_status = SyncStatus.idle
    meta.error_message = None
    meta.last_sync_time = None
    return meta


def make_provider_event(event_id: str, changed_at: str | None = None) -> dict:
    return {
        "id": event_id,
        "name": "Test Event",
        "event_time": "2026-01-11T17:00:00+00:00",
        "registration_deadline": None,
        "status": "published",
        "number_of_visitors": 0,
        "changed_at": changed_at,
        "place": {
            "id": "place-1",
            "name": "Place",
            "city": "Moscow",
            "address": "Addr",
        },
    }


def make_provider(pages: list[list[dict]]) -> MagicMock:
    """Создать мок провайдера с iter_pages возвращающим заданные страницы."""

    async def _iter_pages(**kwargs):
        for page in pages:
            yield page

    provider = MagicMock()
    provider.iter_pages = _iter_pages
    return provider


@pytest.mark.anyio
async def test_first_sync_uses_initial_changed_at():
    """Первая синхронизация запрашивает события с 2000-01-01."""
    meta = make_meta(last_changed_at=None)

    sync_meta_repo = AsyncMock()
    sync_meta_repo.get_or_create.return_value = meta

    called_with = {}

    async def _iter_pages(changed_at=None):
        called_with["changed_at"] = changed_at
        return
        yield  # noqa: unreachable

    provider = MagicMock()
    provider.iter_pages = _iter_pages

    use_case = SyncEventsUseCase(
        AsyncMock(), sync_meta_repo, provider, InMemoryTTLCache()
    )
    await use_case.execute()

    assert called_with["changed_at"] == "2000-01-01"


@pytest.mark.anyio
async def test_subsequent_sync_uses_last_changed_at():
    """Повторная синхронизация использует сохранённую дату."""
    last_dt = datetime(2026, 1, 5, tzinfo=timezone.utc)
    meta = make_meta(last_changed_at=last_dt)

    sync_meta_repo = AsyncMock()
    sync_meta_repo.get_or_create.return_value = meta

    called_with = {}

    async def _iter_pages(changed_at=None):
        called_with["changed_at"] = changed_at
        return
        yield  # noqa: unreachable

    provider = MagicMock()
    provider.iter_pages = _iter_pages

    use_case = SyncEventsUseCase(
        AsyncMock(), sync_meta_repo, provider, InMemoryTTLCache()
    )
    await use_case.execute()

    assert called_with["changed_at"] == "2026-01-05"


@pytest.mark.anyio
async def test_sync_invalidates_seats_cache():
    """После синхронизации кеш мест инвалидируется для всех обновлённых событий."""
    meta = make_meta()
    sync_meta_repo = AsyncMock()
    sync_meta_repo.get_or_create.return_value = meta

    provider = make_provider(
        pages=[[make_provider_event("event-1"), make_provider_event("event-2")]]
    )

    cache = InMemoryTTLCache()
    await cache.set("event-1", ["A1"])
    await cache.set("event-2", ["B1"])

    use_case = SyncEventsUseCase(AsyncMock(), sync_meta_repo, provider, cache)
    await use_case.execute()

    assert await cache.get("event-1") is None
    assert await cache.get("event-2") is None


@pytest.mark.anyio
async def test_sync_sets_failed_status_on_provider_error():
    """При ошибке провайдера статус меняется на failed и исключение пробрасывается."""
    meta = make_meta()
    sync_meta_repo = AsyncMock()
    sync_meta_repo.get_or_create.return_value = meta

    async def _iter_pages(**kwargs):
        raise Exception("Connection timeout")
        yield  # noqa: unreachable

    provider = MagicMock()
    provider.iter_pages = _iter_pages

    use_case = SyncEventsUseCase(
        AsyncMock(), sync_meta_repo, provider, InMemoryTTLCache()
    )

    with pytest.raises(Exception, match="Connection timeout"):
        await use_case.execute()

    assert meta.sync_status == SyncStatus.failed
    assert "Connection timeout" in meta.error_message


@pytest.mark.anyio
async def test_sync_sets_running_then_success():
    """Во время синхронизации статус running, после — success."""
    statuses = []
    meta = make_meta()

    async def capture_save(m):
        statuses.append(m.sync_status)

    sync_meta_repo = AsyncMock()
    sync_meta_repo.get_or_create.return_value = meta
    sync_meta_repo.save.side_effect = capture_save

    use_case = SyncEventsUseCase(
        AsyncMock(), sync_meta_repo, make_provider(pages=[[]]), InMemoryTTLCache()
    )
    await use_case.execute()

    assert statuses[0] == SyncStatus.running
    assert statuses[-1] == SyncStatus.success
