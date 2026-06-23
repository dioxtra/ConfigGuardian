"""sudoers configuration analyzer."""

from pathlib import Path

from configguardian.analyzers.generic import AnalysisResult, BaseAnalyzer


class SudoersAnalyzer(BaseAnalyzer):
    """Analyze sudoers policy risks."""

    def supports(self, path: Path) -> bool:
        """Return whether this analyzer supports sudoers files."""
        return path.name == "sudoers"

    def analyze(self, path: Path, content: str) -> list[AnalysisResult]:
        """Analyze sudoers content."""
        if "NOPASSWD:ALL" in "".join(content.split()):
            return [
                AnalysisResult(
                    file_path=str(path),
                    severity="HIGH",
                    reason="Passwordless sudo for all commands enabled",
                )
            ]
        return []
