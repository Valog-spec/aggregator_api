import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr


class TicketCreate(BaseModel):
    """Данные для регистрации на событие."""

    event_id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    seat: str
    idempotency_key: Optional[str] = None


class TicketCreated(BaseModel):
    """Ответ после успешной регистрации."""

    ticket_id: str


class TicketCancelled(BaseModel):
    """Ответ после успешной отмены регистрации."""

    success: bool = True
