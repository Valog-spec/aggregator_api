"""Репозиторий для работы с билетами."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ticket import Ticket


class TicketRepository:
    """Доступ к данным билетов в БД."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Args:
            session: Активная асинхронная сессия SQLAlchemy.
        """
        self._session = session

    async def create(
        self,
        ticket_id: str,
        event_id: uuid.UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        """Сохранить билет, полученный от провайдера.

        Args:
            ticket_id: Идентификатор билета от Events Provider API.
            event_id: UUID события.
            first_name: Имя участника.
            last_name: Фамилия участника.
            email: Email участника.
            seat: Номер места.

        Returns:
            Созданный объект билета.
        """
        ticket = Ticket(
            ticket_id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        self._session.add(ticket)

        return ticket

    async def get_by_ticket_id(self, ticket_id: str) -> Ticket | None:
        """Найти билет по ticket_id провайдера.

        Args:
            ticket_id: Идентификатор билета от Events Provider API.

        Returns:
            Объект билета или ``None``, если не найден.
        """
        result = await self._session.execute(
            select(Ticket).where(Ticket.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, ticket: Ticket) -> None:
        """Удалить билет из БД.

        Args:
            ticket: Объект билета, полученный из сессии.
        """

        await self._session.delete(ticket)
        await self._session.flush()
