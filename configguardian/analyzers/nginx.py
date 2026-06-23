"""nginx configuration analyzer."""

from pathlib import Path

from configguardian.analyzers.generic import AnalysisResult, BaseAnalyzer


class NginxAnalyzer(BaseAnalyzer):
    """Analyze nginx configuration risks."""

    def supports(self, path: Path) -> bool:
        """Return whether this analyzer supports nginx.conf."""
        return path.name == "nginx.conf"

    def analyze(self, path: Path, content: str) -> list[AnalysisResult]:
        """Analyze nginx content."""
        lowered = content.lower()
        if "root /;" in lowered or "alias /;" in lowered:
            return [
                AnalysisResult(str(path), "HIGH", "Nginx serving from filesystem root")
            ]
        if "x-frame-options off" in lowered or "content-security-policy off" in lowered:
            return [
                AnalysisResult(str(path), "MEDIUM", "Nginx security headers disabled")
            ]
        return []
