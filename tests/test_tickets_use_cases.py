import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.models.event import EventStatus
from src.schemas.ticket import TicketCreate
from src.use_cases.tickets_use_cases import CancelTicketUseCase, CreateTicketUseCase


def make_ticket_data(**kwargs) -> TicketCreate:
    defaults = dict(
        event_id=uuid.uuid4(),
        first_name="Иван",
        last_name="Иванов",
        email="ivan@example.com",
        seat="A15",
    )
    defaults.update(kwargs)
    return TicketCreate(**defaults)


@pytest.mark.anyio
async def test_create_ticket_event_not_found():
    """Возвращает 404, если событие не найдено."""
    event_repo = AsyncMock()
    event_repo.get_by_id.return_value = None

    use_case = CreateTicketUseCase(AsyncMock(), event_repo, AsyncMock())

    with pytest.raises(HTTPException) as exc_info:
        await use_case.execute(make_ticket_data())

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_create_ticket_event_not_published():
    """Возвращает 400, если событие ещё не опубликовано."""
    event = MagicMock()
    event.status = EventStatus.new

    event_repo = AsyncMock()
    event_repo.get_by_id.return_value = event

    use_case = CreateTicketUseCase(AsyncMock(), event_repo, AsyncMock())

    with pytest.raises(HTTPException) as exc_info:
        await use_case.execute(make_ticket_data())

    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_create_ticket_success():
    """Успешная регистрация: вызывается провайдер и сохраняется билет."""
    event_id = uuid.uuid4()

    event = MagicMock()
    event.status = EventStatus.published

    event_repo = AsyncMock()
    event_repo.get_by_id.return_value = event

    provider = AsyncMock()
    provider.register.return_value = "ticket-uuid-123"

    ticket_repo = AsyncMock()

    use_case = CreateTicketUseCase(ticket_repo, event_repo, provider)
    data = make_ticket_data(event_id=event_id)
    result = await use_case.execute(data)

    assert result.ticket_id == "ticket-uuid-123"
    provider.register.assert_called_once_with(
        event_id=str(event_id),
        first_name="Иван",
        last_name="Иванов",
        email="ivan@example.com",
        seat="A15",
    )
    ticket_repo.create.assert_called_once()


@pytest.mark.anyio
async def test_create_ticket_provider_error_not_saved():
    """Если провайдер вернул ошибку — в нашу БД ничего не пишем."""
    event = MagicMock()
    event.status = EventStatus.published

    event_repo = AsyncMock()
    event_repo.get_by_id.return_value = event

    provider = AsyncMock()
    provider.register.side_effect = Exception("Seat already taken")

    ticket_repo = AsyncMock()

    use_case = CreateTicketUseCase(ticket_repo, event_repo, provider)

    with pytest.raises(Exception):
        await use_case.execute(make_ticket_data())

    ticket_repo.create.assert_not_called()


@pytest.mark.anyio
async def test_cancel_ticket_not_found():
    """Возвращает 404, если билет не найден."""
    ticket_repo = AsyncMock()
    ticket_repo.get_by_ticket_id.return_value = None

    use_case = CancelTicketUseCase(ticket_repo, AsyncMock())

    with pytest.raises(HTTPException) as exc_info:
        await use_case.execute("nonexistent-ticket")

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_cancel_ticket_success():
    """Успешная отмена: вызывается провайдер и билет удаляется из БД."""
    ticket = MagicMock()
    ticket.ticket_id = "ticket-123"
    ticket.event_id = uuid.uuid4()

    ticket_repo = AsyncMock()
    ticket_repo.get_by_ticket_id.return_value = ticket

    provider = AsyncMock()

    use_case = CancelTicketUseCase(ticket_repo, provider)
    result = await use_case.execute("ticket-123")

    assert result.success is True
    provider.unregister.assert_called_once_with(
        event_id=str(ticket.event_id),
        ticket_id="ticket-123",
    )
    ticket_repo.delete.assert_called_once_with(ticket)
