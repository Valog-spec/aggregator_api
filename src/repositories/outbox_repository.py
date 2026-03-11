import uuid
from typing import Any, Dict, List

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.outbox import Outbox, OutboxStatus


class OutboxRepository:
    """Репозиторий для работы с outbox таблицей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Outbox:
        """
        Создает запись в outbox.

        ВНИМАНИЕ: Не делает flush/commit, так как является частью
        общей транзакции с TicketRepository!
        """
        outbox = Outbox(
            event_type=event_type,
            payload=payload,
        )
        self._session.add(outbox)
        return outbox

    async def get_pending_messages(
        self, limit: int = 100, max_retries: int = 3
    ) -> List[Outbox]:
        """Получить сообщения для отправки (с блокировкой)"""
        stmt = (
            select(Outbox)
            .where(
                and_(
                    Outbox.status == OutboxStatus.pending,
                    Outbox.retry_count < max_retries,
                    Outbox.event_type == "ticket.created",
                )
            )
            .order_by(Outbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_sent(self, message_id: uuid.UUID):
        """Пометить как отправленное"""
        stmt = (
            update(Outbox)
            .where(Outbox.id == message_id)
            .values(
                status=OutboxStatus.sent,
            )
        )
        await self._session.execute(stmt)

    async def increment_retry(self, message_id: uuid.UUID, error: str):
        """Увеличить счетчик попыток"""
        stmt = (
            update(Outbox)
            .where(Outbox.id == message_id)
            .values(
                retry_count=Outbox.retry_count + 1,
            )
        )
        await self._session.execute(stmt)

    async def commit(self):
        """Явный коммит всей транзакции"""
        await self._session.commit()
