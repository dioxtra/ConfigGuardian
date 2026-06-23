"""Severity scoring helpers."""


def normalize_severity(value: str) -> str:
    """Normalize severity values for storage and display."""
    normalized = value.upper()
    # TODO: Validate against a formal enum.
    return normalized

