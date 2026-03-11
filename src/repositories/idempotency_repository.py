import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.idempotency import IdempotencyKey
from src.schemas.ticket import TicketCreate


class IdempotencyRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_key(self, key: str) -> Optional[IdempotencyKey]:
        """Найти запись по ключу идемпотентности"""
        stmt = select(IdempotencyKey).where(IdempotencyKey.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, key: str, ticket_id: str, data: TicketCreate
    ) -> IdempotencyKey:
        """Сохранить ключ идемпотентности"""
        idempotency = IdempotencyKey(
            key=key,
            ticket_id=uuid.UUID(ticket_id),
            event_id=data.event_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            seat=data.seat,
        )
        self._session.add(idempotency)
        return idempotency
