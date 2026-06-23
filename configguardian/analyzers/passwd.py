"""passwd file analyzer."""

from pathlib import Path

from configguardian.analyzers.generic import AnalysisResult, BaseAnalyzer


class PasswdAnalyzer(BaseAnalyzer):
    """Detect account-related changes."""

    def supports(self, path: Path) -> bool:
        """Return whether this analyzer supports passwd."""
        return path.name == "passwd"

    def analyze(self, path: Path, content: str) -> list[AnalysisResult]:
        """Analyze passwd content."""
        for line in content.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0] != "root" and parts[2] == "0":
                return [
                    AnalysisResult(
                        file_path=str(path),
                        severity="HIGH",
                        reason="Non-root account with UID 0 detected",
                    )
                ]
        return []
