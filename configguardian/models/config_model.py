"""Configuration file models."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from configguardian.utils.constants import DEFAULT_WATCHED_FILES


class AppConfig(BaseModel):
    """Runtime configuration loaded from YAML."""

    model_config = ConfigDict(frozen=True)

    watched_files: list[Path] = Field(
        default_factory=lambda: [Path(path) for path in DEFAULT_WATCHED_FILES]
    )
    database_path: Path
    enabled_notifiers: list[str] = Field(default_factory=list)

