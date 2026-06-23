# ConfigGuardian

**ConfigGuardian** is a lightweight Python CLI for monitoring critical Linux
configuration files, storing versioned snapshots, comparing changes, and
highlighting risky configuration edits.

It helps answer three practical questions:

- What changed?
- When did it change?
- Is the change risky?

ConfigGuardian stores its data locally in SQLite, uses `watchdog` for real-time
file monitoring, and keeps the architecture modular so new analyzers and alert
providers can be added cleanly.

---

## What It Does

ConfigGuardian can:

- monitor important Linux configuration files
- create SHA256-based snapshots
- store file content, size, hash, and timestamp
- compare old and new snapshots
- show a timeline of file events
- restore a file from a selected snapshot
- detect risky configuration patterns
- send alerts through modular notifier providers
- generate an HTML report

It is designed for Linux administrators, security engineers, homelab users, and
DevSecOps teams who want a simple local configuration integrity tool.

---

## Default Watched Files

By default, ConfigGuardian watches:

```text
/etc/ssh/sshd_config
/etc/passwd
/etc/sudoers
/etc/crontab
/etc/nginx/nginx.conf
```

You can provide your own watched files with a YAML config:

```yaml
watched_files:
  - /etc/ssh/sshd_config
  - /etc/passwd
  - /opt/myapp/app.conf
```

---

## Features

### Real-Time Monitoring

- Watches files with `watchdog`
- Handles created, modified, and deleted events
- Supports custom YAML config files
- Uses lightweight debounce protection for noisy filesystem events

### Snapshots

Each snapshot stores:

- file path
- SHA256 hash
- full file content
- file size
- UTC timestamp

### Diff

ConfigGuardian can compare:

- two explicit snapshot IDs
- the latest two snapshots for each file

The diff output highlights added and removed lines.

### Timeline

Events are stored in SQLite and can be listed from the CLI:

```bash
configguardian timeline
```

### Rollback

ConfigGuardian can restore a file from a snapshot ID. Before restoring, it
creates a timestamped backup of the current file.

Example backup name:

```text
sshd_config.20260623143001.configguardian.bak
```

### Security Analysis

Built-in rules detect common risky changes:

| File | Rule | Severity |
| --- | --- | --- |
| `/etc/ssh/sshd_config` | `PermitRootLogin yes` | HIGH |
| `/etc/ssh/sshd_config` | `PasswordAuthentication yes` | MEDIUM |
| `/etc/sudoers` | `NOPASSWD:ALL` | HIGH |
| `/etc/passwd` | new regular user detected | MEDIUM |
| `/etc/passwd` | root-like user detected | HIGH |
| `/etc/crontab` | new cron entry | MEDIUM |
| `/etc/crontab` | suspicious commands such as `wget`, `curl`, `bash -i` | HIGH |
| `/etc/nginx/nginx.conf` | disabled security headers | MEDIUM |
| `/etc/nginx/nginx.conf` | root serving enabled | HIGH |

### Alerts

ConfigGuardian includes notifier classes for:

- Discord webhooks
- Telegram bots
- Slack webhooks
- SMTP email

The alert manager filters low-severity noise by default, suppresses duplicate
alerts, and prevents repeated alert spam with cooldown logic.

### Reports

The HTML report includes:

- event count
- snapshot count
- severity distribution
- recent events
- latest snapshots
- file-level snapshot statistics

---

## Requirements

- Python 3.12+
- Linux for real `/etc` monitoring
- Windows or macOS can be used for development and local sandbox tests

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd ConfigGuardian
```

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install ConfigGuardian:

```bash
python -m pip install -e ".[dev]"
```

Check the CLI:

```bash
configguardian --help
```

---

## Quick Start

Initialize local storage:

```bash
configguardian init
```

Create snapshots:

```bash
configguardian snapshot
```

Show status:

```bash
configguardian status
```

Show event timeline:

```bash
configguardian timeline
```

Generate an HTML report:

```bash
configguardian report
```

The report is written to:

```text
configguardian/data/reports/report.html
```

---

## Safe Local Demo

Use this demo first. It does not modify real system files.

```bash
mkdir -p /tmp/configguardian-demo
echo "PermitRootLogin no" > /tmp/configguardian-demo/sshd_config

cat > /tmp/configguardian-demo/config.yaml <<EOF
watched_files:
  - /tmp/configguardian-demo/sshd_config
EOF

configguardian init
configguardian snapshot --config /tmp/configguardian-demo/config.yaml

echo "PermitRootLogin yes" > /tmp/configguardian-demo/sshd_config
configguardian snapshot --config /tmp/configguardian-demo/config.yaml

configguardian diff
configguardian report
```

---

## Windows Sandbox Demo

Windows does not have Linux `/etc` paths. Use a local file for testing:

```powershell
mkdir sandbox
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
configguardian report
```

---

## Real Linux Monitoring

For real system files, ConfigGuardian may need elevated permissions.

Create an initial snapshot:

```bash
sudo .venv/bin/configguardian snapshot
```

Start monitoring:

```bash
sudo .venv/bin/configguardian monitor
```

Stop monitoring with `Ctrl+C`.

View events:

```bash
configguardian timeline
```

Generate a report:

```bash
configguardian report
```

---

## Command Reference

### `configguardian init`

Initializes the local SQLite database.

```bash
configguardian init
```

### `configguardian status`

Shows basic project status.

```bash
configguardian status
```

### `configguardian config`

Shows effective configuration.

```bash
configguardian config
configguardian config --config examples/config.yaml
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

### `configguardian timeline`

Shows recent file events.

```bash
configguardian timeline
configguardian timeline --limit 50
```

### `configguardian rollback`

Restores a file from a snapshot.

```bash
configguardian rollback 2
```

Always test rollback on temporary files before using it on important system
configuration files.

### `configguardian report`

Generates an HTML report.

```bash
configguardian report
```

### `configguardian monitor`

Starts real-time monitoring.

```bash
configguardian monitor
configguardian monitor --config examples/config.yaml
```

---

## Architecture

```text
configguardian/
  cli.py                 Typer command-line interface
  main.py                Python entrypoint

  core/
    database.py          SQLite persistence layer
    monitor.py           watchdog event pipeline
    snapshot.py          snapshot creation
    diff_engine.py       snapshot comparison
    rollback.py          restore with backup
    timeline.py          event timeline
    analyzer.py          plugin-based security analysis
    hashing.py           SHA256 helpers
    scheduler.py         scheduled task shell

  alerts/
    base.py              notifier interface
    manager.py           filtering, cooldown, dispatch
    discord.py           Discord notifier
    telegram.py          Telegram notifier
    slack.py             Slack notifier
    email.py             SMTP email notifier

  reports/
    html_report.py       HTML report
    markdown_report.py   Markdown report
    json_report.py       JSON report

  models/
    snapshot_model.py
    event_model.py
    config_model.py
    alert_model.py
```

---

## Data Flow

```text
1. watchdog detects a file event
2. Monitor normalizes the event
3. Database stores the event
4. AnalyzerEngine checks for risky patterns
5. AlertManager filters and deduplicates alerts
6. Notifiers send alerts when configured
7. Snapshot, diff, timeline, and report commands inspect stored data
```

---

## Storage

ConfigGuardian uses SQLite directly. No ORM is required.

Main tables:

- `events`
- `snapshots`
- `alerts`
- `timeline`

Runtime database files are stored under:

```text
configguardian/data/
```

---

## Testing

Run the test suite:

```bash
python -m pytest
```

Run a syntax/import check:

```bash
python -m compileall -q configguardian tests
```

Expected current test result:

```text
14 passed
```

---

## Security Notes

- Use the safe local demo before touching real system files.
- Run against `/etc` only when you understand the permission and rollback impact.
- Keep notification tokens, webhooks, and SMTP credentials out of Git.
- ConfigGuardian is a local configuration monitoring tool, not a replacement for
  a SIEM, EDR, or full compliance scanner.

---

## Roadmap

- GitHub Actions CI
- Systemd service example
- More Linux hardening rules
- Richer HTML report charts
- Packaged releases
- SIEM-friendly export formats

---

## License

MIT

