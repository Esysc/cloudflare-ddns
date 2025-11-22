"""Unit tests covering the main logic of the ddns.py script."""

import os
import sys
import unittest
from unittest.mock import patch, Mock
import importlib


class TestMainLogic(unittest.TestCase):
    """Test cases for the ddns.py main function."""

    def setUp(self):
        """Set environment and reload ddns module before each test."""
        self.env_patcher = patch.dict(
            os.environ,
            {
                'CLOUDFLARE_API_TOKEN': 'fake-token',
                'DDNS_ZONE_NAME': 'example.com',
                'DDNS_DNS_NAME': 'host.example.com',
                'DDNS_DRY_RUN': '0',
            },
            clear=True,
        )
        self.env_patcher.start()
        self.ddns = importlib.reload(importlib.import_module("ddns"))

    def tearDown(self):
        """Remove environment patch after each test."""
        self.env_patcher.stop()

    def test_main_record_needs_update(self):
        """Test main() updates record when IP differs."""
        ddns = self.ddns
        with patch.object(ddns, 'update_a_record') as mock_update, \
             patch.object(ddns, 'get_public_ip', return_value='192.0.2.100'), \
             patch.object(
                 ddns,
                 'get_dns_records',
                 return_value=[{'id': 'rec-123', 'content': '192.0.2.1'}]
             ), \
             patch.object(ddns, 'get_zone_id', return_value='fake-zone-id'), \
             patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()
            self.assertEqual(exit_code, 0)
            mock_update.assert_called_once_with('fake-zone-id', 'rec-123', '192.0.2.100')

    def test_main_record_already_up_to_date(self):
        """Test main() returns up-to-date exit code when IP matches."""
        ddns = self.ddns
        with patch.object(ddns, 'update_a_record') as mock_update, \
             patch.object(ddns, 'get_public_ip', return_value='192.0.2.1'), \
             patch.object(
                 ddns,
                 'get_dns_records',
                 return_value=[{'id': 'rec-123', 'content': '192.0.2.1'}]
             ), \
             patch.object(ddns, 'get_zone_id', return_value='fake-zone-id'), \
             patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()
            self.assertEqual(exit_code, 7)
            mock_update.assert_not_called()

    def test_main_network_error_returns_3(self):
        """Test main() returns network error exit code on exception."""
        ddns = self.ddns
        with patch.object(
                ddns,
                'get_public_ip',
                side_effect=ddns.requests.exceptions.RequestException("fail")
             ), \
             patch.object(ddns, 'get_dns_records', return_value=[{'id': 'rec-123'}]), \
             patch.object(ddns, 'get_zone_id', return_value='fake-zone-id'), \
             patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()
            self.assertEqual(exit_code, 3)

    def test_main_dry_run_does_not_update(self):
        """Test main() does not call patch request during dry run."""
        ddns = self.ddns
        with patch.dict(os.environ, {'DDNS_DRY_RUN': '1'}, clear=False):
            importlib.reload(ddns)
            with patch.object(ddns.requests, 'patch') as mock_patch, \
                 patch.object(ddns, 'get_public_ip', return_value='192.0.2.100'), \
                 patch.object(
                 ddns,
                 'get_dns_records',
                 return_value=[{'id': 'rec-123', 'content': '192.0.2.1'}]
                 ), \
                 patch.object(ddns, 'get_zone_id', return_value='fake-zone-id'), \
                 patch.object(sys, 'argv', ['ddns.py']):
                exit_code = ddns.main()
                self.assertEqual(exit_code, 0)
                mock_patch.assert_not_called()

    def test_main_zone_not_found_returns_4(self):
        """Test main() returns exit code for missing zone."""
        ddns = self.ddns
        with patch.object(ddns, 'get_zone_id', return_value=None), \
             patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()
            self.assertEqual(exit_code, 4)

    def test_main_no_dns_records_returns_1(self):
        """Test main() returns exit code when no DNS A records found."""
        ddns = self.ddns
        with patch.object(ddns, 'get_zone_id', return_value='fake-zone-id'), \
             patch.object(ddns, 'get_dns_records', return_value=[]), \
             patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()
            self.assertEqual(exit_code, 1)

    def test_main_missing_env_vars_returns_2_and_6(self):
        """Test various missing environment variable scenarios."""
        ddns_mod = importlib.import_module("ddns")

        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(ddns_mod)
            with patch.object(sys, 'argv', ['ddns.py']):
                self.assertEqual(ddns_mod.main(), 2)

        with patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'token'}, clear=True):
            importlib.reload(ddns_mod)
            with patch.object(sys, 'argv', ['ddns.py']):
                self.assertEqual(ddns_mod.main(), 6)

        with patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'token',
                                    'DDNS_ZONE_NAME': 'zone'}, clear=True):
            importlib.reload(ddns_mod)
            with patch.object(sys, 'argv', ['ddns.py']):
                self.assertEqual(ddns_mod.main(), 6)


class TestGenericHttpRequest(unittest.TestCase):
    """Test generic_http_request handling JSON and text methods."""

    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            'CLOUDFLARE_API_TOKEN': 'fake-token',
        }, clear=True)
        self.env_patcher.start()
        self.ddns = importlib.reload(importlib.import_module("ddns"))

    def tearDown(self):
        self.env_patcher.stop()

    def test_json_response_success(self):
        """Test JSON response is correctly parsed."""
        ddns = self.ddns
        with patch.object(ddns.requests, 'request') as mock_request:
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock()
            mock_resp.headers = {'Content-Type': 'application/json'}
            mock_resp.json.return_value = {'key': 'value'}
            mock_request.return_value = mock_resp

            result = ddns.generic_http_request('GET', 'http://fakeurl', expect_json=True)
            self.assertEqual(result, {'key': 'value'})

    def test_json_response_invalid_json_raises(self):
        """Test invalid JSON response raises ValueError."""
        ddns = self.ddns
        with patch.object(ddns.requests, 'request') as mock_request:
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock()
            mock_resp.headers = {'Content-Type': 'application/json'}
            mock_resp.json.side_effect = ValueError("Invalid JSON")
            mock_request.return_value = mock_resp

            with self.assertRaises(ValueError):
                ddns.generic_http_request('GET', 'http://fakeurl', expect_json=True)

    def test_json_response_wrong_content_type_raises(self):
        """Test wrong content-type raises ValueError on JSON expectation."""
        ddns = self.ddns
        with patch.object(ddns.requests, 'request') as mock_request:
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock()
            mock_resp.headers = {'Content-Type': 'text/html'}
            mock_request.return_value = mock_resp

            with self.assertRaises(ValueError):
                ddns.generic_http_request('GET', 'http://fakeurl', expect_json=True)

    def test_text_response_success(self):
        """Test plain text response is returned correctly. """
        ddns = self.ddns
        with patch.object(ddns.requests, 'request') as mock_request:
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock()
            mock_resp.headers = {'Content-Type': 'text/plain'}
            mock_resp.text = 'plain response text'
            mock_request.return_value = mock_resp

            result = ddns.generic_http_request('GET', 'http://fakeurl', expect_json=False)
            self.assertEqual(result, 'plain response text')


if __name__ == '__main__':
    unittest.main()
