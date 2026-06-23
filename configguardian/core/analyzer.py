"""Plugin-based security analyzer engine for ConfigGuardian."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, Optional, TypedDict

from configguardian.utils.logger import get_logger


class AnalysisResult(TypedDict):
    """Normalized security analyzer result."""

    file_path: str
    severity: str
    reason: str
    recommendation: str


EventPayload = Mapping[str, Any]


class BaseAnalyzer(ABC):
    """Base class for security analyzer plugins."""

    fallback = False

    @abstractmethod
    def can_handle(self, event: EventPayload) -> bool:
        """Return whether this analyzer can handle the event."""

    @abstractmethod
    def analyze(self, event: EventPayload) -> Optional[AnalysisResult]:
        """Analyze an event and return a security insight."""


class AnalyzerEngine:
    """Register and run analyzer plugins."""

    SEVERITY_ORDER = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    def __init__(self, analyzers: Optional[list[BaseAnalyzer]] = None) -> None:
        self._analyzers: list[BaseAnalyzer] = analyzers or []
        self.logger = get_logger(__name__)

    def register(self, analyzer: BaseAnalyzer) -> None:
        """Register an analyzer plugin."""
        self._analyzers.append(analyzer)

    def analyze(self, event: EventPayload) -> list[AnalysisResult]:
        """Run matching analyzers for an event and return normalized results."""
        results: list[AnalysisResult] = []
        fallback_results: list[AnalysisResult] = []

        for analyzer in self._analyzers:
            try:
                if not analyzer.can_handle(event):
                    continue

                result = analyzer.analyze(event)
            except Exception as exc:
                self.logger.exception(
                    "Analyzer %s failed: %s",
                    analyzer.__class__.__name__,
                    exc,
                )
                continue

            if result is None:
                continue

            normalized = self._normalize_result(result, event)
            if analyzer.fallback:
                fallback_results.append(normalized)
            else:
                results.append(normalized)

        return results or fallback_results

    def get_worst_result(
        self,
        results: list[AnalysisResult],
    ) -> Optional[AnalysisResult]:
        """Return the highest-severity result from a result list."""
        if not results:
            return None

        return max(
            results,
            key=lambda result: self._severity_score(result.get("severity", "LOW")),
        )

    def _normalize_result(
        self,
        result: Mapping[str, Any],
        event: EventPayload,
    ) -> AnalysisResult:
        """Normalize analyzer output to the public result contract."""
        return {
            "file_path": self._string_value(result, "file_path")
            or self._string_value(event, "file_path"),
            "severity": self._normalize_severity(
                self._string_value(result, "severity") or "LOW"
            ),
            "reason": self._string_value(result, "reason")
            or "Configuration file event detected",
            "recommendation": self._string_value(result, "recommendation")
            or "Review the file change and confirm it was authorized.",
        }

    def _normalize_severity(self, severity: str) -> str:
        """Normalize severity to a known value."""
        normalized = severity.upper()
        if normalized not in self.SEVERITY_ORDER:
            return "LOW"
        return normalized

    def _severity_score(self, severity: str) -> int:
        """Return numeric severity rank."""
        return self.SEVERITY_ORDER.get(severity.upper(), 0)

    @staticmethod
    def _string_value(source: Mapping[str, Any], key: str) -> str:
        """Return a safe string value from a mapping."""
        value = source.get(key)
        if value is None:
            return ""
        return str(value)


class ContentAnalyzer(BaseAnalyzer):
    """Common helpers for content-based analyzers."""

    def _content(self, event: EventPayload) -> str:
        """Return current content from a flexible event payload."""
        return (
            self._string_value(event, "content")
            or self._string_value(event, "new_content")
            or self._string_value(event, "details")
        )

    def _previous_content(self, event: EventPayload) -> str:
        """Return previous content from a flexible event payload."""
        return self._string_value(event, "previous_content") or self._string_value(
            event,
            "old_content",
        )

    def _file_path(self, event: EventPayload) -> str:
        """Return event file path as a string."""
        return self._string_value(event, "file_path")

    def _result(
        self,
        event: EventPayload,
        severity: str,
        reason: str,
        recommendation: str,
    ) -> AnalysisResult:
        """Build a normalized analyzer result."""
        return {
            "file_path": self._file_path(event),
            "severity": severity.upper(),
            "reason": reason,
            "recommendation": recommendation,
        }

    def can_handle(self, event: EventPayload) -> bool:
        """Return whether this analyzer can handle the event."""
        return bool(self._file_path(event))

    def analyze(self, event: EventPayload) -> Optional[AnalysisResult]:
        """Analyze an event and return a security insight."""
        return None

    @staticmethod
    def _string_value(source: EventPayload, key: str) -> str:
        """Return a safe string value from a mapping."""
        value = source.get(key)
        if value is None:
            return ""
        return str(value)


class SshAnalyzer(ContentAnalyzer):
    """Analyze sshd_config events."""

    def can_handle(self, event: EventPayload) -> bool:
        """Return whether this analyzer handles the SSH daemon config."""
        return self._file_path(event) == "/etc/ssh/sshd_config"

    def analyze(self, event: EventPayload) -> Optional[AnalysisResult]:
        """Detect insecure SSH daemon directives."""
        content = self._content(event)

        if self._has_directive(content, "PermitRootLogin", "yes"):
            return self._result(
                event,
                "HIGH",
                "PermitRootLogin is enabled",
                "Set PermitRootLogin to no or prohibit-password.",
            )

        if self._has_directive(content, "PasswordAuthentication", "yes"):
            return self._result(
                event,
                "MEDIUM",
                "PasswordAuthentication is enabled",
                "Prefer key-based authentication and set PasswordAuthentication to no.",
            )

        return None

    @staticmethod
    def _has_directive(content: str, directive: str, value: str) -> bool:
        """Return whether content contains an uncommented directive value."""
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) >= 2 and parts[0] == directive and parts[1].lower() == value:
                return True

        return False


class SudoersAnalyzer(ContentAnalyzer):
    """Analyze sudoers events."""

    def can_handle(self, event: EventPayload) -> bool:
        """Return whether this analyzer handles sudoers."""
        return self._file_path(event) == "/etc/sudoers"

    def analyze(self, event: EventPayload) -> Optional[AnalysisResult]:
        """Detect risky sudoers permissions."""
        content = "".join(self._content(event).split())

        if "NOPASSWD:ALL" in content:
            return self._result(
                event,
                "HIGH",
                "Passwordless sudo for all commands is enabled",
                "Limit NOPASSWD usage to specific commands or require authentication.",
            )

        return None


class PasswdAnalyzer(ContentAnalyzer):
    """Analyze passwd events."""

    def can_handle(self, event: EventPayload) -> bool:
        """Return whether this analyzer handles passwd."""
        return self._file_path(event) == "/etc/passwd"

    def analyze(self, event: EventPayload) -> Optional[AnalysisResult]:
        """Detect newly added users."""
        previous_lines = self._account_lines(self._previous_content(event))
        current_lines = self._account_lines(self._content(event))

        if not previous_lines or len(current_lines) <= len(previous_lines):
            return None

        new_lines = [line for line in current_lines if line not in previous_lines]
        if any(self._is_root_like_user(line) for line in new_lines):
            return self._result(
                event,
                "HIGH",
                "Root-like user account was added",
                "Review the new account UID, shell, groups, and authorization source.",
            )

        return self._result(
            event,
            "MEDIUM",
            "New user account was added",
            "Verify the account owner, shell, UID, and creation approval.",
        )

    @staticmethod
    def _account_lines(content: str) -> list[str]:
        """Return non-empty passwd account lines."""
        return [line for line in content.splitlines() if line.strip()]

    @staticmethod
    def _is_root_like_user(line: str) -> bool:
        """Return whether a passwd line describes a root-like user."""
        parts = line.split(":")
        if len(parts) < 7:
            return False

        username = parts[0].lower()
        uid = parts[2]
        shell = parts[6]
        return uid == "0" or (
            username in {"root", "admin"} and shell != "/usr/sbin/nologin"
        )


class CronAnalyzer(ContentAnalyzer):
    """Analyze crontab events."""

    def can_handle(self, event: EventPayload) -> bool:
        """Return whether this analyzer handles crontab."""
        return self._file_path(event) == "/etc/crontab"

    def analyze(self, event: EventPayload) -> Optional[AnalysisResult]:
        """Detect new and suspicious cron entries."""
        content = self._content(event)
        previous_content = self._previous_content(event)
        new_entries = self._new_cron_entries(previous_content, content)
        search_content = "\n".join(new_entries) if new_entries else content

        if self._has_suspicious_command(search_content):
            return self._result(
                event,
                "HIGH",
                "Suspicious command found in cron configuration",
                "Review the cron entry and remove unauthorized network or shell payloads.",
            )

        if new_entries:
            return self._result(
                event,
                "MEDIUM",
                "New cron entry was added",
                "Confirm the schedule, command owner, and business justification.",
            )

        return None

    @staticmethod
    def _new_cron_entries(previous_content: str, content: str) -> list[str]:
        """Return cron lines that appear in current content but not previous content."""
        previous_entries = {
            line.strip()
            for line in previous_content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        current_entries = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return [line for line in current_entries if line not in previous_entries]

    @staticmethod
    def _has_suspicious_command(content: str) -> bool:
        """Return whether cron content contains suspicious command patterns."""
        lowered = content.lower()
        suspicious_patterns = ("wget", "curl", "bash -i")
        return any(pattern in lowered for pattern in suspicious_patterns)


class NginxAnalyzer(ContentAnalyzer):
    """Analyze nginx configuration events."""

    def can_handle(self, event: EventPayload) -> bool:
        """Return whether this analyzer handles nginx.conf."""
        return self._file_path(event) == "/etc/nginx/nginx.conf"

    def analyze(self, event: EventPayload) -> Optional[AnalysisResult]:
        """Detect risky nginx configuration changes."""
        content = self._content(event).lower()

        if self._root_serving_enabled(content):
            return self._result(
                event,
                "HIGH",
                "Nginx appears to serve directly from filesystem root",
                "Set root to a dedicated web directory with least-privilege ownership.",
            )

        if self._security_headers_disabled(content):
            return self._result(
                event,
                "MEDIUM",
                "Nginx security headers appear to be disabled",
                "Enable appropriate security headers such as X-Frame-Options and CSP.",
            )

        return None

    @staticmethod
    def _root_serving_enabled(content: str) -> bool:
        """Return whether nginx root points to filesystem root."""
        return "root /;" in content or "alias /;" in content

    @staticmethod
    def _security_headers_disabled(content: str) -> bool:
        """Return whether common security headers are disabled or missing."""
        disabled_markers = (
            "# add_header x-frame-options",
            "# add_header content-security-policy",
            "x-frame-options off",
            "content-security-policy off",
        )
        return any(marker in content for marker in disabled_markers)


class GenericAnalyzer(ContentAnalyzer):
    """Fallback analyzer for all events."""

    fallback = True

    def can_handle(self, event: EventPayload) -> bool:
        """Return True for every event with a file path."""
        return bool(self._file_path(event))

    def analyze(self, event: EventPayload) -> AnalysisResult:
        """Return a low-severity generic insight."""
        return self._result(
            event,
            "LOW",
            "Configuration file event detected",
            "Review the file change and confirm it was authorized.",
        )


def create_default_engine() -> AnalyzerEngine:
    """Create an analyzer engine with built-in analyzer plugins."""
    return AnalyzerEngine(
        analyzers=[
            SshAnalyzer(),
            SudoersAnalyzer(),
            PasswdAnalyzer(),
            CronAnalyzer(),
            NginxAnalyzer(),
            GenericAnalyzer(),
        ]
    )

