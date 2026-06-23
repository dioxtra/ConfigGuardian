"""Risk explanation helpers."""

from configguardian.analyzers.generic import AnalysisResult


def explain_finding(finding: AnalysisResult) -> str:
    """Return a human-readable explanation for a finding."""
    # TODO: Expand with local rules or optional LLM integration.
    return finding.reason

