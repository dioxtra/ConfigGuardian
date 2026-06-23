"""Alert data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlertMessage(BaseModel):
    """Notification payload sent to providers."""

    model_config = ConfigDict(frozen=True)

    severity: str
    file_path: str
    reason: str
    created_at: datetime


class AlertRecord(BaseModel):
    """Stored alert delivery record."""

    model_config = ConfigDict(frozen=True)

    id: Optional[int] = None
    provider: str
    severity: str
    message: str
    sent_at: Optional[datetime] = None

