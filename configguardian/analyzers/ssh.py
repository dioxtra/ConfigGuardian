"""SSH daemon configuration analyzer."""

from pathlib import Path

from configguardian.analyzers.generic import AnalysisResult, BaseAnalyzer


class SshAnalyzer(BaseAnalyzer):
    """Detect risky sshd_config directives."""

    def supports(self, path: Path) -> bool:
        """Return whether this analyzer supports sshd_config."""
        return path.name == "sshd_config"

    def analyze(self, path: Path, content: str) -> list[AnalysisResult]:
        """Analyze SSH daemon configuration content."""
        findings: list[AnalysisResult] = []
        active_lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        active_content = "\n".join(active_lines)
        if "PermitRootLogin yes" in active_content:
            findings.append(
                AnalysisResult(str(path), "HIGH", "PermitRootLogin enabled")
            )
        if "PasswordAuthentication yes" in active_content:
            findings.append(
                AnalysisResult(str(path), "HIGH", "PasswordAuthentication enabled")
            )
        return findings
