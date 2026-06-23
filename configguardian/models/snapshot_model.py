"""Snapshot data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Snapshot(BaseModel):
    """Stored snapshot metadata and content."""

    model_config = ConfigDict(frozen=True)

    id: Optional[int] = None
    file_path: str
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    modified_at: datetime
    content: str
    created_at: datetime

