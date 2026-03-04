import httpx
from fastapi import HTTPException

from src.clients.base import EventsProviderClient
from src.models.event import EventStatus
from src.repositories.event_repository import EventRepository
from src.repositories.ticket_repository import TicketRepository
from src.schemas.ticket import TicketCancelled, TicketCreate, TicketCreated


class CreateTicketUseCase:
    """Регистрация участника на событие через Events Provider API."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        event_repo: EventRepository,
        provider_client: EventsProviderClient,
    ) -> None:
        self._ticket_repo = ticket_repo
        self._event_repo = event_repo
        self._client = provider_client

    async def execute(self, data: TicketCreate) -> TicketCreated:
        """
        Зарегистрировать участника на событие.

        Алгоритм:
        1. Проверяет существование события в локальной БД.
        2. Проверяет, что событие опубликовано (status == published).
        3. Вызывает Events Provider API для регистрации.
        4. Сохраняет ticket_id и данные участника в локальной БД.

        Args:
            data: Данные регистрации (event_id, имя, email, место).

        Returns:
            ticket_id, выданный провайдером.

        Raises:
            HTTPException: 404, если событие не найдено.
            HTTPException: 400, если событие не опубликовано или место занято.
        """
        event = await self._event_repo.get_by_id(data.event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        if event.status != EventStatus.published:
            raise HTTPException(
                status_code=400, detail="Событие недоступно для регистрации"
            )

        try:
            ticket_id = await self._client.register(
                event_id=str(data.event_id),
                first_name=data.first_name,
                last_name=data.last_name,
                email=data.email,
                seat=data.seat,
            )
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get(
                    "detail", "Ошибка регистрации у провайдера"
                )
            except Exception:
                detail = "Ошибка регистрации у провайдера"
            raise HTTPException(
                status_code=exc.response.status_code, detail=detail
            ) from exc

        await self._ticket_repo.create(
            ticket_id=ticket_id,
            event_id=data.event_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            seat=data.seat,
        )
        return TicketCreated(ticket_id=ticket_id)


class CancelTicketUseCase:
    """Отмена регистрации участника через Events Provider API."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        provider_client: EventsProviderClient,
    ) -> None:
        self._ticket_repo = ticket_repo
        self._client = provider_client

    async def execute(self, ticket_id: str) -> TicketCancelled:
        """
        Отменить регистрацию по ticket_id.

        Args:
            ticket_id: Идентификатор билета от провайдера.

        Returns:
            Подтверждение отмены.

        Raises:
            HTTPException: 404, если билет не найден.
        """
        ticket = await self._ticket_repo.get_by_ticket_id(ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Билет не найден")

        try:
            await self._client.unregister(
                event_id=str(ticket.event_id),
                ticket_id=ticket_id,
            )
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get(
                    "detail", "Ошибка отмены регистрации у провайдера"
                )
            except Exception:
                detail = "Ошибка отмены регистрации у провайдера"
            raise HTTPException(
                status_code=exc.response.status_code, detail=detail
            ) from exc
        await self._ticket_repo.delete(ticket)
        return TicketCancelled()
