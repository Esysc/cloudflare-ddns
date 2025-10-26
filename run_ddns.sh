#!/usr/bin/env bash
set -euo pipefail

# Lightweight runner for ddns.py using a virtual environment located at ./venv
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
# We open a file descriptor 9 and flock it. If another process holds the lock,
# we exit quietly.
LOCKFILE="/tmp/ddns-runner.lock"
exec 9>"$LOCKFILE" || exit 1
if ! flock -n 9 ; then
  echo "Another instance is running, exiting." >&2
  exit 0
fi

TOKEN_ARG=""
ZONE_ARG=""
NAME_ARG=""
POSITIONAL_TOKEN=""
while [ ${#} -gt 0 ]; do
  case "$1" in
    --token|-t)
      TOKEN_ARG="$2"; shift 2;;
    --zone|-z)
      ZONE_ARG="$2"; shift 2;;
    --name|-n)
      NAME_ARG="$2"; shift 2;;
    --help|-h)
      usage; exit 0;;
    --*)
      echo "Unknown option: $1" >&2; usage; exit 2;;
    *)
      if [ -z "$POSITIONAL_TOKEN" ]; then
        POSITIONAL_TOKEN="$1"
      else
        echo "Unexpected positional argument: $1" >&2; usage; exit 2
      fi
      shift
      ;;
  esac
done

# Prefer explicit token flag, then positional, then env
TOKEN_ARG="${TOKEN_ARG:-$POSITIONAL_TOKEN}"
if [ -n "$TOKEN_ARG" ]; then
  export CLOUDFLARE_API_TOKEN="$TOKEN_ARG"
fi

# Optionally read token from a file if env/arg not provided.
# Default locations: $CLOUDFLARE_TOKEN_FILE env, then ~/.cloudflare_token, then ./cloudflare_token
TOKEN_FILE="${CLOUDFLARE_TOKEN_FILE:-$HOME/.cloudflare_token}"
if [ ! -n "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$TOKEN_FILE" ]; then
  # warn if permissions are too open
  perms=$(stat -f "%A" "$TOKEN_FILE" 2>/dev/null || stat -c "%a" "$TOKEN_FILE" 2>/dev/null || echo "600")
  if [ "$perms" != "600" ]; then
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
