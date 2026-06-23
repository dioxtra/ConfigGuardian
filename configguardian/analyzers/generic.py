"""Base analyzer contracts and generic fallback analyzer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnalysisResult:
    """Structured risk analysis result."""

    file_path: str
    severity: str
    reason: str


class BaseAnalyzer(ABC):
    """Base class for analyzer plugins."""

    @abstractmethod
    def supports(self, path: Path) -> bool:
        """Return whether this analyzer handles the path."""

    @abstractmethod
    def analyze(self, path: Path, content: str) -> list[AnalysisResult]:
        """Analyze file content and return risk findings."""


class GenericAnalyzer(BaseAnalyzer):
    """Fallback analyzer for unclassified config files."""

    def supports(self, path: Path) -> bool:
        """Return True for any file path."""
        _ = path
        return True

    def analyze(self, path: Path, content: str) -> list[AnalysisResult]:
        """Return generic analysis findings."""
        _ = content
        return [
            AnalysisResult(
                file_path=str(path),
                severity="LOW",
                reason="Generic configuration change detected",
            )
        ]
