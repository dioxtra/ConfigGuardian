# ConfigGuardian

ConfigGuardian is a lightweight Python CLI for monitoring critical Linux
configuration files, storing versioned snapshots, comparing changes, analyzing
risk, and generating local security reports.

It is built for system administrators, security engineers, DevSecOps teams, and
homelab users who want a simple, local, auditable way to answer:

- What changed?
- When did it change?
- Which file changed?
- Is the change risky?
- Can I restore a previous version?

ConfigGuardian uses SQLite for local storage, `watchdog` for real-time file
monitoring, `typer` for the CLI, and a modular analyzer and notifier design so
the project can grow without turning into a monolith.

## Project Status

ConfigGuardian is currently a working GitHub MVP. It is not an enterprise SIEM
or a full compliance platform, but the core workflows are implemented and
testable:

- file monitoring
- snapshot creation
- snapshot diffing
- timeline listing
- rollback with backup
- security analysis
- alert dispatch architecture
- HTML report generation
- GitHub Actions CI

The project is intended to be a clean foundation for future hardening,
packaging, and production deployment work.

## Features

### File Monitoring

ConfigGuardian can monitor important Linux configuration files in real time.

Default watched files:

```text
/etc/ssh/sshd_config
/etc/passwd
/etc/sudoers
/etc/crontab
/etc/nginx/nginx.conf
```

The monitor handles:

- created events
- modified events
- deleted events
- duplicate event debounce
- optional YAML-based watched file configuration

### Snapshots

Snapshots store the state of watched files in SQLite.

Each snapshot includes:

- file path
- SHA256 hash
- full file content
- file size
- UTC timestamp

### Diff Engine

The diff engine compares snapshots and shows:

- added lines
- removed lines
- changed content summary

You can compare explicit snapshot IDs or let ConfigGuardian compare the latest
available snapshots.

### Timeline

All file events are persisted and can be listed from the CLI.

Example:

```bash
configguardian timeline
```

### Rollback

ConfigGuardian can restore a file from a selected snapshot ID. Before restoring
the snapshot content, it creates a timestamped backup of the current file.

Example backup name:

```text
sshd_config.20260623143001.configguardian.bak
```

### Security Analysis

ConfigGuardian includes a plugin-style analyzer engine in
`configguardian/core/analyzer.py`.

Built-in analyzer coverage:

| File | Rule | Severity |
| --- | --- | --- |
| `/etc/ssh/sshd_config` | `PermitRootLogin yes` | HIGH |
| `/etc/ssh/sshd_config` | `PasswordAuthentication yes` | MEDIUM |
| `/etc/sudoers` | `NOPASSWD:ALL` | HIGH |
| `/etc/passwd` | new user detected | MEDIUM |
| `/etc/passwd` | root-like user detected | HIGH |
| `/etc/crontab` | new cron entry | MEDIUM |
| `/etc/crontab` | suspicious commands such as `wget`, `curl`, `bash -i` | HIGH |
| `/etc/nginx/nginx.conf` | disabled security headers | MEDIUM |
| `/etc/nginx/nginx.conf` | root directory serving enabled | HIGH |

Analyzer results use a standard schema:

```python
{
    "file_path": "...",
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "reason": "...",
    "recommendation": "...",
}
```

### Alerts

ConfigGuardian has a provider-based notification system.

Supported providers:

- Discord webhook
- Telegram bot
- Slack webhook
- SMTP email

Alert manager behavior:

- filters alerts below the configured severity threshold
- ignores duplicate alerts
- groups repeated alerts during cooldown
- sends notifications in background workers
- logs notifier failures without crashing the monitor

### HTML Reports

The report command generates a local HTML report containing:

- event summary
- severity distribution
- recent events
- latest snapshots
- file-level statistics

```bash
configguardian report
```

Default report path:

```text
configguardian/data/reports/report.html
```

## Installation

### Requirements

- Python 3.12 or newer
- Linux for real `/etc` monitoring
- Windows, macOS, or Linux for development and sandbox testing

### Clone

```bash
git clone https://github.com/dioxtra/ConfigGuardian.git
cd ConfigGuardian
```

### Create a Virtual Environment

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify the CLI:

```bash
configguardian --help
```

## Quick Start

Initialize local storage:

```bash
configguardian init
```

Create snapshots:

```bash
configguardian snapshot
```

Show current status:

```bash
configguardian status
```

Show recorded events:

```bash
configguardian timeline
```

Generate an HTML report:

```bash
configguardian report
```

## Deployment

ConfigGuardian can be deployed as a systemd service so the monitor keeps running
in the background and starts automatically after reboot.

```bash
sudo pip install -e .
sudo mkdir -p /etc/configguardian
sudo cp examples/config.yaml /etc/configguardian/config.yaml
sudo bash deploy/install.sh
```

See [deploy/README.md](deploy/README.md) for full systemd deployment
documentation.

## Safe Demo

Use this demo before monitoring real system files. It only touches files under
`/tmp`.

```bash
mkdir -p /tmp/configguardian-demo
echo "PermitRootLogin no" > /tmp/configguardian-demo/sshd_config

cat > /tmp/configguardian-demo/config.yaml <<EOF
watched_files:
  - /tmp/configguardian-demo/sshd_config
alerts:
  providers: {}
EOF

configguardian init
configguardian snapshot --config /tmp/configguardian-demo/config.yaml

echo "PermitRootLogin yes" > /tmp/configguardian-demo/sshd_config
configguardian snapshot --config /tmp/configguardian-demo/config.yaml

configguardian diff
configguardian timeline
configguardian report
```

## Real Linux Usage

Monitoring files under `/etc` usually requires elevated permissions.

Create an initial baseline:

```bash
sudo configguardian snapshot
```

Start real-time monitoring:

```bash
sudo configguardian monitor
```

Stop monitoring with `Ctrl+C`.

Review activity:

```bash
configguardian timeline
configguardian diff
configguardian report
```

## Windows Development Demo

Windows does not have Linux `/etc` paths, so use a local sandbox file.

```powershell
New-Item -ItemType Directory -Force sandbox | Out-Null
Set-Content sandbox\app.conf "enabled=true"

@"
watched_files:
  - sandbox\app.conf
"@ | Set-Content examples\local.yaml

configguardian init
configguardian snapshot --config examples\local.yaml

Set-Content sandbox\app.conf "enabled=false"
configguardian snapshot --config examples\local.yaml
configguardian diff
```

## Configuration

ConfigGuardian can read YAML configuration files through `--config`.

Example:

```yaml
watched_files:
  - /etc/ssh/sshd_config
  - /etc/passwd
  - /etc/sudoers
  - /etc/crontab
  - /etc/nginx/nginx.conf

alerts:
  min_severity: MEDIUM
  cooldown_seconds: 30
  providers:
    discord:
      enabled: false
      webhook_url: https://discord.com/api/webhooks/your-webhook-id/your-webhook-token
    telegram:
      enabled: false
      bot_token: your-telegram-bot-token
      chat_id: your-telegram-chat-id
    slack:
      enabled: false
      webhook_url: https://hooks.slack.com/services/your/webhook/url
    email:
      enabled: false
      smtp_host: smtp.example.com
      smtp_port: 587
      sender: cg@example.com
      recipient: oncall@example.com
      username: cg@example.com
      password: replace-with-secret
      use_tls: true
```

Use the config file:

```bash
configguardian monitor --config examples/config.yaml
configguardian snapshot --config examples/config.yaml
configguardian config --config examples/config.yaml
```

Never commit real webhook URLs, bot tokens, SMTP passwords, or production
secrets.

## CLI Reference

### `configguardian init`

Initializes local SQLite storage.

```bash
configguardian init
```

### `configguardian monitor`

Starts real-time file monitoring.

```bash
configguardian monitor
configguardian monitor --config examples/config.yaml
```

### `configguardian snapshot`

Creates snapshots for watched files.

```bash
configguardian snapshot
configguardian snapshot --config examples/config.yaml
```

### `configguardian diff`

Compares snapshots.

```bash
configguardian diff
configguardian diff --old 1 --new 2
```

### `configguardian rollback`

Restores a file from a snapshot ID and creates a backup first.

```bash
configguardian rollback 2
```

Test rollback on temporary files before using it on important system
configuration files.

### `configguardian timeline`

Lists recorded file events.

```bash
configguardian timeline
configguardian timeline --limit 50
```

### `configguardian report`

Generates an HTML report.

```bash
configguardian report
```

### `configguardian config`

Shows the effective watched file configuration.

```bash
configguardian config
configguardian config --config examples/config.yaml
```

### `configguardian status`

Shows basic local status.

```bash
configguardian status
```

## Architecture

```text
configguardian/
  cli.py                Typer CLI
  main.py               Python entrypoint

  core/
    monitor.py          watchdog event pipeline
    database.py         SQLite persistence layer
    snapshot.py         snapshot creation
    diff_engine.py      snapshot comparison
    rollback.py         file restore with backup
    timeline.py         event queries
    analyzer.py         plugin-based risk analysis
    scheduler.py        background scheduler service
    config_loader.py    YAML alert manager loader

  alerts/
    base.py             notifier contract
    manager.py          filtering, cooldown, deduplication, dispatch
    discord.py          Discord webhook notifier
    telegram.py         Telegram Bot API notifier
    slack.py            Slack webhook notifier
    email.py            SMTP email notifier

  reports/
    html_report.py      HTML report generation
    markdown_report.py  Markdown report generation
    json_report.py      JSON report generation

  models/
    snapshot_model.py
    event_model.py
    config_model.py
    alert_model.py

  utils/
    logger.py
    constants.py
    helpers.py
    file_utils.py
```

## Data Flow

```text
watchdog
  -> Monitor
  -> Database
  -> AnalyzerEngine
  -> AlertManager
  -> Notifiers
```

Snapshot, diff, timeline, rollback, and report commands all read from the same
local SQLite storage.

## Storage

ConfigGuardian uses SQLite directly and does not use an ORM.

Main tables:

- `events`
- `snapshots`
- `alerts`
- `timeline`

Runtime files are created under:

```text
configguardian/data/
```

Runtime database files, caches, logs, and generated reports should not be
committed to Git.

## Testing

Run the test suite:

```bash
python -m pytest
```

Run syntax/import validation:

```bash
python -m compileall -q configguardian tests
```

Run linting:

```bash
python -m ruff check configguardian tests
```

Run type checking:

```bash
python -m mypy configguardian --ignore-missing-imports
```

## Continuous Integration

The GitHub Actions workflow runs on pushes and pull requests to `main`.

CI jobs:

- `lint` with Ruff on Python 3.12
- `test` on Python 3.12 and 3.13
- `typecheck` with mypy on Python 3.12
- coverage XML upload through Codecov

## Security Notes

- Start with the safe demo before touching real system files.
- Use elevated permissions only when needed.
- Be careful with rollback on production configuration files.
- Keep webhook URLs, bot tokens, SMTP passwords, and other secrets out of Git.
- ConfigGuardian is a local configuration integrity and visibility tool. It is
  not a replacement for a SIEM, EDR, backup platform, or compliance scanner.

## Roadmap

- richer HTML report charts and filtering
- more Linux hardening rules
- systemd service example
- packaged releases
- SIEM-friendly export formats
- release automation

## License

MIT
