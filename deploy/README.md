# ConfigGuardian systemd Deployment

This guide explains how to run ConfigGuardian as a long-running systemd service
on a Linux host.

The service runs:

```bash
configguardian monitor --config /etc/configguardian/config.yaml
```

## 1. Prerequisites

Before installing the systemd service, make sure the host has:

- Python 3.12 or newer
- a Linux system with systemd
- ConfigGuardian installed from the project root

Install ConfigGuardian from the project root:

```bash
python -m pip install -e .
```

For system-wide service usage, install it where systemd can find the
`configguardian` entry point. The provided service file expects:

```text
/usr/local/bin/configguardian
```

## 2. Create the Config File

Create the production config directory:

```bash
sudo mkdir -p /etc/configguardian
```

Copy the example config:

```bash
sudo cp examples/config.yaml /etc/configguardian/config.yaml
```

Edit the config:

```bash
sudo nano /etc/configguardian/config.yaml
```

Update these fields:

- `watched_files`: the files ConfigGuardian should monitor
- `alerts.providers.discord`: Discord webhook settings
- `alerts.providers.telegram`: Telegram bot token and chat ID
- `alerts.providers.slack`: Slack webhook settings
- `alerts.providers.email`: SMTP settings

Keep all real secrets out of Git.

## 3. Choose a User

ConfigGuardian can run as root or as a dedicated service user.

### Option A: Simple root-based setup

This is the easiest setup when ConfigGuardian needs to read protected files
under `/etc` and you do not want to configure file permissions yet.

Edit `deploy/configguardian.service`:

```ini
User=root
```

Make sure the dedicated user line remains commented:

```ini
# User=configguardian
```

### Option B: Recommended dedicated service user

Create a dedicated non-login user:

```bash
sudo useradd -r -s /sbin/nologin configguardian
```

Make the config readable by that user:

```bash
sudo chown configguardian /etc/configguardian/config.yaml
```

Edit `deploy/configguardian.service`:

```ini
User=configguardian
```

Make sure the root line remains commented:

```ini
# User=root
```

Grant read access to watched files as needed. For protected files under `/etc`,
you may need ACLs, group membership, or a more specific permission strategy.

## 4. Install and Start

Run the installer from the project root:

```bash
sudo bash deploy/install.sh
```

The script will:

- copy `deploy/configguardian.service` to `/etc/systemd/system/`
- run `systemctl daemon-reload`
- enable the service at boot
- start the service
- print `systemctl status configguardian`

## 5. Managing the Service

View live logs:

```bash
journalctl -u configguardian -f
```

Check status:

```bash
systemctl status configguardian
```

Stop the service:

```bash
sudo systemctl stop configguardian
```

Restart the service:

```bash
sudo systemctl restart configguardian
```

Disable autostart:

```bash
sudo systemctl disable configguardian
```

## 6. Uninstall

Stop the service:

```bash
sudo systemctl stop configguardian
```

Disable autostart:

```bash
sudo systemctl disable configguardian
```

Remove the unit file:

```bash
sudo rm /etc/systemd/system/configguardian.service
```

Reload systemd:

```bash
sudo systemctl daemon-reload
```
