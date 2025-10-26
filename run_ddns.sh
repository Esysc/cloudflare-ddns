#!/usr/bin/env bash
set -euo pipefail

# Lightweight runner for ddns.py using a virtual environment located at ./venv

# Ignore SIGHUP (hang-up signal) to prevent the script from being terminated
# when run from a cron job or other non-interactive shell.
trap '' HUP
# Usage examples:
#   ./run_ddns.sh                          # runs ddns.py (dry-run by default)
#   ./run_ddns.sh --token <TOKEN>          # pass token on the CLI
#   ./run_ddns.sh --zone example.com --name host.example.com
#   CLOUDFLARE_API_TOKEN=... ./run_ddns.sh  # or export token in env
#   DDNS_ZONE_NAME=example.com DDNS_DNS_NAME=host.example.com ./run_ddns.sh
#
# The script accepts these flags:
#   --token | -t TOKEN   : Cloudflare API token (falls back to CLOUDFLARE_API_TOKEN env)
#   --zone  | -z ZONE    : Cloudflare zone name (falls back to DDNS_ZONE_NAME env)
#   --name  | -n NAME    : DNS record name to update (falls back to DDNS_DNS_NAME env)
#
# If no flags are provided, env vars are used where available. The script will
# pass --zone/--name to `ddns.py` when provided.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HERE/venv"
SCRIPT="$HERE/ddns.py"

# --- Log Redirection ---
# Redirect all stdout and stderr from this script to the log file defined by
# the DDNS_LOG_FILE environment variable, defaulting to ddns.log.
# This unifies the shell script's logs with the Python script's logs.
LOG_FILE="${DDNS_LOG_FILE:-$HERE/ddns.log}"
exec > >(tee -a "$LOG_FILE") 2>&1

usage() {
  cat <<'USAGE' >&2
Usage: run_ddns.sh [--token TOKEN] [--zone ZONE] [--name NAME]

Options:
  --token, -t TOKEN   Cloudflare API token (falls back to CLOUDFLARE_API_TOKEN env)
  --zone,  -z ZONE    Cloudflare zone name (falls back to DDNS_ZONE_NAME env)
  --name,  -n NAME    DNS record name to update (falls back to DDNS_DNS_NAME env)
  --help,  -h         Show this help

Examples:
  ./run_ddns.sh --token xxxxx --zone example.com --name host.example.com
  DDNS_ZONE_NAME=example.com DDNS_DNS_NAME=host.example.com ./run_ddns.sh
USAGE
}


# Simple lock to avoid overlapping runs. Uses /tmp so it doesn't require root.
if command -v flock >/dev/null 2>&1; then
  # We open a file descriptor 9 and flock it. If another process holds the lock,
  # we exit quietly.
  LOCKFILE="/tmp/ddns-runner.lock"
  exec 9>"$LOCKFILE" || exit 1
  if ! flock -n 9 ; then
    echo "Another instance is running, exiting." >&2
    exit 0
  fi
else
  echo "Warning: 'flock' command not found. Proceeding without lock. Multiple instances may run." >&2
fi

TOKEN_ARG=""
ZONE_ARG=""
NAME_ARG=""

# More robust argument parsing to handle --opt=val and "--opt val" as a single arg
ARGS=()
for arg in "$@"; do
  # If an argument contains a space, split it into two.
  # This handles cases from cron jobs where "--token value" is a single string.
  if [[ "$arg" == *" "* ]]; then
    # Use read -a to robustly split the argument into an array.
    read -r -a split_arg <<< "$arg"
    ARGS+=("${split_arg[@]}")
  else
    ARGS+=("$arg")
  fi
done
set -- "${ARGS[@]}"

while [ ${#} -gt 0 ]; do
  case "$1" in
    --token=*) TOKEN_ARG="${1#*=}"; shift 1;;
    --token|-t) TOKEN_ARG="$2"; shift 2;;
    --zone=*) ZONE_ARG="${1#*=}"; shift 1;;
    --zone|-z) ZONE_ARG="$2"; shift 2;;
    --name=*) NAME_ARG="${1#*=}"; shift 1;;
    --name|-n) NAME_ARG="$2"; shift 2;;
    --help|-h)
      usage; exit 0;;
    --*)
      echo "Unknown option: $1" >&2; usage; exit 2;;
    *)
      echo "Unexpected positional argument: $1" >&2; usage; exit 2
      ;;
  esac
done

if [ -n "$TOKEN_ARG" ]; then
  export CLOUDFLARE_API_TOKEN="$TOKEN_ARG"
fi

# Optionally read token from a file if env/arg not provided.
# Default locations: $CLOUDFLARE_TOKEN_FILE env, then ~/.cloudflare_token, then ./cloudflare_token
TOKEN_FILE="${CLOUDFLARE_TOKEN_FILE:-$HOME/.cloudflare_token}"
if [ ! -n "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$TOKEN_FILE" ]; then
  # warn if permissions are too open
  perms=$(stat -c "%a" "$TOKEN_FILE" 2>/dev/null || stat -f "%A" "$TOKEN_FILE" 2>/dev/null || echo "???")
  if [[ "$perms" != "600" && "$perms" != "-rw-------" ]]; then
    echo "Warning: token file $TOKEN_FILE should have permissions 600 (chmod 600)" >&2
  fi
  # read only the first line, trim CR/LF and whitespace
  token_raw=$(sed -n '1p' "$TOKEN_FILE" 2>/dev/null || true)
  token_trimmed=$(printf '%s' "$token_raw" | tr -d '\r\n' | awk '{$1=$1;print}')
  if [ -n "$token_trimmed" ]; then
    export CLOUDFLARE_API_TOKEN="$token_trimmed"
  fi
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR..."
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but not found in PATH" >&2
    exit 1
  fi
  python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
# Activate venv
if [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck source=/dev/null
  source "$VENV_DIR/bin/activate"
  echo "Activated virtual environment: $VENV_DIR"

  # Install/upgrade packages after activation
  python -m pip install --upgrade pip
  if ! python -c "import requests" >/dev/null 2>&1; then
    echo "Installing required Python packages into venv..."
    python -m pip install -r "$HERE/requirements.txt"
  fi
else
  echo "Virtual environment activation script not found at $VENV_DIR/bin/activate" >&2
  exit 1
fi

# Determine zone/name to pass to ddns.py: CLI flags take precedence, then env vars
ZONE_ARG="${ZONE_ARG:-${DDNS_ZONE_NAME:-}}"
NAME_ARG="${NAME_ARG:-${DDNS_DNS_NAME:-}}"

if [ -z "$ZONE_ARG" ] || [ -z "$NAME_ARG" ]; then
  echo "Note: zone or name missing; you can provide them with --zone/--name or via DDNS_ZONE_NAME/DDNS_DNS_NAME env vars."
  echo "ddns.py will validate presence and exit if required values are missing."
fi

ARGS=()
if [ -n "$ZONE_ARG" ]; then
  ARGS+=("--zone" "$ZONE_ARG")
fi
if [ -n "$NAME_ARG" ]; then
  ARGS+=("--name" "$NAME_ARG")
fi

echo "Running $SCRIPT ${ARGS[*]}"
python "$SCRIPT" "${ARGS[@]}"
