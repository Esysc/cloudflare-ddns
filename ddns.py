"""Simple DDNS updater for Cloudflare using the REST API.

This script updates all A records for a given name in a Cloudflare zone to
the machine's public IP. It intentionally does NOT contain any secret
values — provide the Cloudflare API token via the environment variable
`CLOUDFLARE_API_TOKEN` or another secret mechanism.

See README.md for usage and deployment notes.
"""
import os
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any, List

# Third-party imports
import requests

# --- Configuration ---
# Zone and DNS names must be provided via command-line arguments or
# environment variables. This file no longer contains hard-coded
# `ZONE_NAME` / `DNS_NAME` values.
#
# CLI args: --zone ZONE_NAME --name DNS_NAME
# Environment variables fallback: DDNS_ZONE_NAME and DDNS_DNS_NAME
# Read token only from the environment (no hard-coded fallback)
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

# If DDNS_DRY_RUN is set to '0' or 'false' (case-insensitive) the script will
# perform real updates. Default is dry-run to avoid accidental changes.
_env_dry = os.getenv('DDNS_DRY_RUN', '1')
DRY_RUN = _env_dry.lower() not in ('0', 'false', 'no')

API_BASE = 'https://api.cloudflare.com/client/v4'
HEADERS = {
    'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}' if CLOUDFLARE_API_TOKEN else '',
    'Content-Type': 'application/json',
}

# --- Logging setup ---
HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.getenv('DDNS_LOG_FILE', os.path.join(HERE, 'ddns.log'))
LOG_LEVEL = os.getenv('DDNS_LOG_LEVEL', 'INFO').upper()

logger = logging.getLogger('ddns')
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
fh.setFormatter(formatter)
logger.addHandler(fh)


def cf_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Perform a GET against the Cloudflare API and return JSON.

    Raises requests.RequestException on network errors.
    """
    url = f"{API_BASE}{path}"
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def cf_patch(path: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform a PATCH against the Cloudflare API (or simulate when dry-run)."""
    if DRY_RUN:
        logger.info(
            "DRY RUN - would PATCH %s with %s",
            path,
            json_data,
        )
        return {"success": True, "result": json_data}
    url = f"{API_BASE}{path}"
    r = requests.patch(url, headers=HEADERS, json=json_data, timeout=15)
    r.raise_for_status()
    return r.json()


def get_zone_id(zone_name: str) -> Optional[str]:
    """Return the Cloudflare zone ID for `zone_name` or None if not found."""
    resp = cf_get('/zones', params={'name': zone_name})
    if not resp.get('success'):
        logger.error(
            'Failed getting zones: %s',
            resp,
        )
        return None
    zones = resp.get('result', [])
    if not zones:
        return None
    return zones[0]['id']


def get_dns_records(zone_id: str, record_name: str, record_type: str = 'A') -> List[Dict[str, Any]]:
    """Return DNS records for a name/type in a zone, or an empty list on error."""
    resp = cf_get(
        f'/zones/{zone_id}/dns_records',
        params={
            'name': record_name,
            'type': record_type,
        },
    )
    if not resp.get('success'):
        logger.error(
            'Failed getting dns records: %s',
            resp,
        )
        return []
    return resp.get('result', [])


def update_a_record(zone_id: str, record_id: str, new_ip: str) -> None:
    """Update an A record identified by `record_id` to `new_ip`."""
    # Use PATCH to update only the content field, preserving all other settings.
    data: Dict[str, Any] = {
        'content': new_ip,
    }
    resp = cf_patch(
        f'/zones/{zone_id}/dns_records/{record_id}',
        json_data=data,
    )
    logger.info(
        'Update response (or dry-run): %s',
        resp,
    )


def get_public_ip() -> str:
    """Return the current public IPv4 address as a string.

    Raises on network failures.
    """
    return requests.get('https://api.ipify.org', timeout=10).text.strip()


def main() -> int:
    """CLI entrypoint. Parse args and update A records in Cloudflare.

    Returns an exit code suitable for `sys.exit`.
    """
    exit_code = 0
    parser = argparse.ArgumentParser(description='Simple DDNS updater for Cloudflare')
    parser.add_argument('--zone', '-z', help='Cloudflare zone name (e.g. example.com)')
    parser.add_argument('--name', '-n', help='DNS record name to update (e.g. host.example.com)')
    args = parser.parse_args()

    try:
        # Determine zone and dns name: CLI args preferred, then environment variables
        zone_name = args.zone or os.getenv('DDNS_ZONE_NAME')
        dns_name = args.name or os.getenv('DDNS_DNS_NAME')

        # --- Validation Guard Clauses ---
        if not CLOUDFLARE_API_TOKEN:
            logger.error('CLOUDFLARE_API_TOKEN not set')
            return 2

        if not zone_name or not dns_name:
            logger.error('Zone and DNS name must be provided')
            return 6

        zone_id = get_zone_id(zone_name)
        if not zone_id:
            logger.error('Zone not found')
            return 4

        # --- Main Logic ---
        records = get_dns_records(zone_id, dns_name, 'A')
        if not records:
            logger.info('No A record found for %s in zone %s', dns_name, zone_name)
            return 0

        new_ip = get_public_ip()
        any_updated = False
        for record in records:
            if record.get('content') == new_ip:
                logger.info('Record %s already up-to-date - IP: %s', record.get('id'), new_ip)
                continue
            update_a_record(zone_id, record['id'], new_ip)
            any_updated = True

        if not any_updated:
            logger.info('No records needed update')
            return 7  # Special exit code for "up-to-date"
    except requests.exceptions.RequestException as e:
        logger.error('A network error occurred: %s', e)
        exit_code = 3  # Generic network error exit code

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
