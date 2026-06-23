"""Event and timeline models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    """File event stored by ConfigGuardian."""

    model_config = ConfigDict(frozen=True)

    id: Optional[int] = None
    file_path: str
    event_type: str
    severity: str
    reason: str
    created_at: datetime

