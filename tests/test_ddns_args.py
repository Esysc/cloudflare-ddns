"""Unit tests for the top-level ddns CLI behavior."""

import importlib
import os
import sys
import unittest
from unittest import mock

import ddns


class TestDDNSArgs(unittest.TestCase):
    """Basic tests for CLI argument/env handling of ddns.main."""

    def setUp(self):
        # Ensure tests do not inherit a token from the environment
        self._orig_env = dict(os.environ)
        os.environ.pop('CLOUDFLARE_API_TOKEN', None)
        os.environ.pop('DDNS_ZONE_NAME', None)
        os.environ.pop('DDNS_DNS_NAME', None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_missing_token_returns_2(self):
        """If no CLOUDFLARE_API_TOKEN is present, main() exits with 2."""
        # Reload module after clearing env so module-level token variable is unset.
        importlib.reload(ddns)

        with mock.patch.object(sys, 'argv', ['ddns.py']):
            rc = ddns.main()
        self.assertEqual(rc, 2)

    def test_token_but_missing_zone_name_returns_6(self):
        """If token is present but zone/name missing, main() exits 6."""
        os.environ['CLOUDFLARE_API_TOKEN'] = 'fake-token'
        importlib.reload(ddns)

        # No zone or name provided on CLI or env -> should return code 6
        with mock.patch.object(sys, 'argv', ['ddns.py']):
            rc = ddns.main()
        self.assertEqual(rc, 6)


if __name__ == '__main__':
    unittest.main()
