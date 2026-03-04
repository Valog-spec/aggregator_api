from typing import Annotated

from fastapi import APIRouter, Depends

from src.dependencies import get_cancel_ticket_use_case, get_create_ticket_use_case
from src.schemas.ticket import TicketCancelled, TicketCreate, TicketCreated
from src.use_cases.tickets_use_cases import CancelTicketUseCase, CreateTicketUseCase

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketCreated, status_code=201)
async def create_ticket(
    data: TicketCreate,
    use_case: Annotated[CreateTicketUseCase, Depends(get_create_ticket_use_case)],
) -> TicketCreated:
    """Зарегистрировать участника на событие.

    Выполняет запрос к Events Provider API.
    Возвращает 404, если событие не найдено.
    Возвращает 400, если событие не опубликовано или место занято.
    """
    return await use_case.execute(data)


@router.delete("/{ticket_id}", response_model=TicketCancelled, status_code=200)
async def cancel_ticket(
    ticket_id: str,
    use_case: Annotated[CancelTicketUseCase, Depends(get_cancel_ticket_use_case)],
) -> TicketCancelled:
    """Отменить регистрацию по ticket_id.

    Выполняет запрос к Events Provider API.
    Возвращает 404, если билет не найден.
    """
    return await use_case.execute(ticket_id)
