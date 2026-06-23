"""Project constants."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PACKAGE_ROOT / "data"
SNAPSHOT_DIR = DATA_ROOT / "snapshots"
REPORT_DIR = DATA_ROOT / "reports"
LOG_DIR = DATA_ROOT / "logs"
DEFAULT_DATABASE_PATH = DATA_ROOT / "database.db"
DEFAULT_REPORT_PATH = REPORT_DIR / "report.html"

DEFAULT_WATCHED_FILES = (
    "/etc/ssh/sshd_config",
    "/etc/passwd",
    "/etc/sudoers",
    "/etc/crontab",
    "/etc/nginx/nginx.conf",
)

READ_CHUNK_SIZE = 1024 * 1024
BACKUP_SUFFIX = ".configguardian.bak"

