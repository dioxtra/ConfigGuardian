"""File system helpers."""

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text_file(path: Path) -> str:
    """Read a text file with safe defaults."""
    return path.read_text(encoding="utf-8", errors="replace")

