# DDNS updater for Cloudflare

This repository contains a small DDNS updater script that updates A records in
a Cloudflare zone to match the host's public IP address.

Rationale
---------
If you host a web server and proxy the site through Cloudflare, DNS records
point to the server's public IP. When the server IP changes (reboot, DHCP,
cloud VM migration), DNS can become stale. This script queries the current
public IP and updates all matching A records for a given name in a Cloudflare
zone so DNS stays correct.

Security
--------
- Do NOT store secrets in source. The script reads the Cloudflare API token
  from the environment variable `CLOUDFLARE_API_TOKEN` (or from a token file).
- Use a scoped Cloudflare API token with least privileges (DNS:Edit for the
  target zone).

Files
-----
- `ddns.py` — main Python script (dry-run by default; reads token from env).
- `run_ddns.sh` — helper that creates/activates a `venv` and runs `ddns.py`.
- `cron.example` — suggested crontab line.
- `ddns.service` / `ddns.timer` — systemd unit and timer examples.

Quick start
-----------
1. Create a virtual environment and install dependencies:

```bash
cd ddns
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip requests
chmod +x run_ddns.sh
```

2. Run the updater (dry-run default):

```bash
export CLOUDFLARE_API_TOKEN="<your_token_here>"
./run_ddns.sh --zone example.com --name host.example.com
```

To perform a real update (be careful):

```bash
DDNS_DRY_RUN=0 ./run_ddns.sh --zone example.com --name host.example.com
```

Usage and flags
---------------
`run_ddns.sh` accepts these options (and forwards `--zone/--name` to `ddns.py`):
- `--token` / `-t` : Cloudflare API token (fallback: `CLOUDFLARE_API_TOKEN` env)
- `--zone`  / `-z` : Cloudflare zone name (fallback: `DDNS_ZONE_NAME` env)
- `--name`  / `-n` : DNS record name to update (fallback: `DDNS_DNS_NAME` env)

The script supports both `--option value` and `--option=value` formats, making it resilient to different shell environments, including restrictive cron job runners.

Examples
--------

Using CLI flags (preferred):

```bash
./run_ddns.sh --token xxxxx --zone example.com --name host.example.com
```

Using environment variables:

```bash
DDNS_ZONE_NAME=example.com DDNS_DNS_NAME=host.example.com CLOUDFLARE_API_TOKEN=xxxx ./run_ddns.sh
```

Backwards compatibility (positional token):

```bash
./run_ddns.sh xxxxx
# with env vars for zone/name
DDNS_ZONE_NAME=example.com DDNS_DNS_NAME=host.example.com ./run_ddns.sh xxxxx
```

Tests
-----
There is a small test suite that validates argument/env validation for
`ddns.py` without making network calls. Run it with:

```bash
python3 -m unittest discover -v
```

Deployment notes
----------------
- Prefer injecting `CLOUDFLARE_API_TOKEN` from your host's environment/secret
  store rather than embedding it in crontab or files.
- Use the included `ddns.timer` / `ddns.service` example or `cron.example` to
  schedule periodic runs (every 15 minutes recommended).

Token file option
-----------------
If you store the token on disk (less recommended), create `~/.cloudflare_token`
with strict permissions and ensure only the first line contains the token:

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
