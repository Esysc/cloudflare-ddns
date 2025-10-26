# DDNS updater for Cloudflare

This repository contains a robust DDNS updater script that updates A records
in a Cloudflare zone to match the host's public IP address. It includes a
feature-rich runner script with venv management, locking, and email
notifications.

Rationale
---------
When self-hosting services behind Cloudflare, DNS records must point to your
server's public IP. If this IP changes (e.g., due to a DHCP lease renewal or
server migration), DNS becomes stale. This script automates the process of
keeping your Cloudflare DNS records in sync with your dynamic public IP.

Security
--------
- Do NOT store secrets in source. The script reads the Cloudflare API token
  from the environment variable `CLOUDFLARE_API_TOKEN` (or from a token file).
- Use a scoped Cloudflare API token with least privileges (DNS:Edit for the
  target zone).

Files
-----
- `ddns.py` — main Python script (dry-run by default; reads token from env).
- `run_ddns.sh` — Self-contained runner that manages a venv, installs dependencies, handles locking, and sends notifications.
- `requirements.txt` — Python dependencies (`requests`, `apprise`).
- `cron.example` — suggested crontab line.
- `ddns.service` / `ddns.timer` — systemd unit and timer examples.

Quick Start
-----------
The `run_ddns.sh` script is designed to be self-contained. It will automatically
create a Python virtual environment (`venv`) and install dependencies on its
first run.

1.  Make the script executable:
    ```bash
    chmod +x run_ddns.sh
    ```

2.  Run the updater (this is a **dry-run** by default). Provide your token, zone, and record name.
    ```bash
    # Set your token in the environment
    export CLOUDFLARE_API_TOKEN="<your_scoped_api_token>"

    # Run the script with your zone and record name
    ./run_ddns.sh --zone example.com --name host.example.com
    ```

3.  To perform a **real update**, set the `DDNS_DRY_RUN` environment variable to `0`.
    ```bash
    DDNS_DRY_RUN=0 ./run_ddns.sh --zone example.com --name host.example.com
    ```

Usage
-----
The `run_ddns.sh` script accepts the following options. It supports both `--option value` and `--option=value` formats, making it resilient to different shell environments.

#### DDNS Options

| Flag | Environment Variable | Description |
|---|---|---|
| `--token, -t` | `CLOUDFLARE_API_TOKEN` | Your Cloudflare API token. |
| `--zone, -z` | `DDNS_ZONE_NAME` | The Cloudflare zone name (e.g., `example.com`). |
| `--name, -n` | `DDNS_DNS_NAME` | The DNS record name to update (e.g., `host.example.com`). |

#### Notification Options

| Flag | Description |
|---|---|
| `--smtp HOST` | SMTP server for email notifications (e.g., `smtp.example.com:587`). |
| `--username EMAIL` | Username for SMTP authentication. |
| `--password PASS` | Password for SMTP authentication (use quotes for special characters). |
| `--recipient EMAIL` | Recipient's email address (if omitted, defaults to the `--username` email). |

Email Notifications
-------------------
The script can send email notifications upon success or failure using Apprise.

**Notifications are sent only when:**
- A DNS record is successfully updated.
- An error occurs during the update process.

**No notification is sent if the script runs and finds the IP address is already up-to-date.**

To enable notifications, provide the SMTP server, username, and password.

#### Example with Notifications
```bash
DDNS_DRY_RUN=0 ./run_ddns.sh \
  --zone example.com \
  --name host.example.com \
  --smtp smtp.gmail.com:587 \
  --username my-email@gmail.com \
  --password "my-app-password" \
  --recipient notifications@example.com
```

Exit Codes
----------
The `ddns.py` script returns specific exit codes to indicate the outcome:

| Code | Meaning | Notification Sent? |
|---|---|---|
| `0` | Success (record was updated). | Yes (Success) |
| `2` | Configuration Error (API token missing). | Yes (Failure) |
| `3` | Network Error (failed to contact Cloudflare or IP service). | Yes (Failure) |
| `4` | Configuration Error (Zone not found). | Yes (Failure) |
| `6` | Configuration Error (Zone or DNS name missing). | Yes (Failure) |
| `7` | No Action Needed (IP address was already up-to-date). | **No** |

Deployment notes
----------------
- The `run_ddns.sh` script will automatically create a `venv` and install dependencies from `requirements.txt` if they are missing.
- Prefer injecting `CLOUDFLARE_API_TOKEN` from your host's environment/secret
  store rather than embedding it in crontab or files.
- Use the included `ddns.timer` / `ddns.service` example or `cron.example` to
  schedule periodic runs (every 15 minutes recommended).

Token file option
-----------------
As an alternative to the environment variable, `run_ddns.sh` can read the token
from a file. The script checks these locations in order:
1. `$CLOUDFLARE_TOKEN_FILE` (if the environment variable is set)
2. `~/.cloudflare_token`

Create the file with strict permissions:

```bash
echo "<your_token>" > ~/.cloudflare_token
chmod 600 ~/.cloudflare_token
```

`run_ddns.sh` will read and trim the first line if no env var/flag is provided.

Locking and non-overlap
------------------------
The runner uses `/tmp/ddns-runner.lock` (flock) to avoid overlapping runs.

License & contribution
----------------------
This utility is MIT-like in spirit — adapt as needed, but never commit
secrets to source. Use CI secrets or a secret manager for deployments.

Pre-commit (optional but recommended)
------------------------------------
This repo includes a `.pre-commit-config.yaml` with recommended checks:

- ruff (auto-fix) and pylint for Python linting
- shellcheck for shell scripts
- trim trailing whitespace and ensure final newline

Install and enable pre-commit locally:

```bash
python3 -m pip install --user pre-commit
pre-commit install
# optionally run against all files once
pre-commit run --all-files
```

If you'd like I can adjust the pre-commit hooks (enable/disable specific
rules, pin different versions, or add black/isort).
