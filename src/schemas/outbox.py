from pydantic import BaseModel, EmailStr

from src.schemas.ticket import TicketCreate


class OutboxPayload(BaseModel):
    """Данные для отправки в Capashino (хранятся в outbox.payload)"""

    ticket_id: str
    event_id: str
    first_name: str
    last_name: str
    email: EmailStr
    seat: str
    notification_text: str

    @classmethod
    def from_ticket_data(cls, ticket_id: str, data: TicketCreate) -> "OutboxPayload":
        """Фабричный метод для создания payload"""
        return cls(
            ticket_id=ticket_id,
            event_id=str(data.event_id),
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            seat=data.seat,
            notification_text=f"Билет куплен: {data.first_name} {data.last_name}, место {data.seat}",
        )
