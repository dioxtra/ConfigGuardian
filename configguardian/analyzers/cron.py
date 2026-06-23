"""cron configuration analyzer."""

from pathlib import Path

from configguardian.analyzers.generic import AnalysisResult, BaseAnalyzer


class CronAnalyzer(BaseAnalyzer):
    """Flag cron changes for review."""

    def supports(self, path: Path) -> bool:
        """Return whether this analyzer supports cron files."""
        return path.name in {"crontab", "cron"}

    def analyze(self, path: Path, content: str) -> list[AnalysisResult]:
        """Analyze cron content."""
        lowered = content.lower()
        if any(pattern in lowered for pattern in ("wget", "curl", "bash -i")):
            return [
                AnalysisResult(str(path), "HIGH", "Suspicious cron command detected")
            ]
        return [
            AnalysisResult(str(path), "MEDIUM", "Cron configuration changed")
        ]
