from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CapashinoRequest(BaseModel):
    """Запрос к API Capashino"""

    message: str
    reference_id: str
    idempotency_key: str


class CapashinoResponse(BaseModel):
    """Ответ от API Capashino"""

    id: str
    user_id: Optional[str] = None
    message: str
    reference_id: str
    created_at: datetime
    idempotency_key: Optional[str] = None
