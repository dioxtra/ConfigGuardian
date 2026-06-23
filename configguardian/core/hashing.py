"""Hashing helpers."""

from pathlib import Path
import hashlib

from configguardian.utils.constants import READ_CHUNK_SIZE


def sha256_file(path: Path) -> str:
    """Return the SHA256 hash for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(READ_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()

