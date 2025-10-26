"""
Tests for the main logic of the ddns.py script, using mocks to isolate
from network operations.
"""
# Standard library imports
import os
import sys
import unittest
from importlib import reload
from unittest.mock import patch

# Add the parent directory to the path to allow importing 'ddns'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ddns  # pylint: disable=import-error,wrong-import-position


class TestMainLogic(unittest.TestCase):
    """Test the main function's logic flows and exit codes."""

    def setUp(self):
        """Set common environment variables for all tests in this class."""
        os.environ['CLOUDFLARE_API_TOKEN'] = 'fake-token'
        os.environ['DDNS_ZONE_NAME'] = 'example.com'
        os.environ['DDNS_DNS_NAME'] = 'host.example.com'
        # Ensure we are not in dry-run mode for these tests to check update calls
        os.environ['DDNS_DRY_RUN'] = '0'
        # Reload the module to ensure it picks up the environment variables set in
        # this setUp method, isolating it from changes made in other test files.
        reload(ddns)

    def tearDown(self):
        """Clean up environment variables after tests."""
        del os.environ['CLOUDFLARE_API_TOKEN']
        del os.environ['DDNS_ZONE_NAME']
        del os.environ['DDNS_DNS_NAME']
        del os.environ['DDNS_DRY_RUN']

    @patch('ddns.update_a_record')
    @patch('ddns.get_public_ip', return_value='192.0.2.100')
    @patch('ddns.get_dns_records')
    @patch('ddns.get_zone_id', return_value='fake-zone-id')
    def test_main_record_needs_update(
        self, mock_get_zone_id, mock_get_dns_records, mock_get_public_ip, mock_update_a_record
    ):
        """Verify main() updates a record and returns exit code 0."""
        # Arrange: Mock get_dns_records to return a record with a different IP
        mock_get_dns_records.return_value = [
            {'id': 'rec-123', 'name': 'host.example.com', 'content': '192.0.2.1'}
        ]

        # Act: Run the main function, mocking sys.argv to prevent it from
        # parsing the unittest runner's arguments.
        with patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()

        # Assert
        self.assertEqual(exit_code, 0)
        mock_get_zone_id.assert_called_once_with('example.com')  # type: ignore # pylint: disable=line-too-long
        mock_get_dns_records.assert_called_once_with(
            'fake-zone-id', 'host.example.com', 'A'
        )  # type: ignore
        mock_get_public_ip.assert_called_once()  # type: ignore
        # Verify that the update function was called with the correct parameters
        mock_update_a_record.assert_called_once_with(
            'fake-zone-id', 'rec-123', '192.0.2.100'
        )  # type: ignore

    @patch('ddns.update_a_record')
    @patch('ddns.get_public_ip', return_value='192.0.2.1')
    @patch('ddns.get_dns_records')
    @patch('ddns.get_zone_id', return_value='fake-zone-id')
    def test_main_record_already_up_to_date(
        self, mock_get_zone_id, mock_get_dns_records, mock_get_public_ip, mock_update_a_record
    ):
        """Verify main() does nothing and returns exit code 7 if IP is current."""
        # Arrange: Mock get_dns_records to return a record with the same IP
        mock_get_dns_records.return_value = [
            {'id': 'rec-123', 'name': 'host.example.com', 'content': '192.0.2.1'}
        ]

        # Act: Run the main function, mocking sys.argv.
        with patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()

        # Assert
        self.assertEqual(exit_code, 7)
        mock_get_zone_id.assert_called_once_with('example.com')  # type: ignore
        mock_get_dns_records.assert_called_once_with( # type: ignore
            'fake-zone-id',
            'host.example.com',
            'A'
        )
        mock_get_public_ip.assert_called_once()  # type: ignore
        # Verify that the update function was NOT called
        mock_update_a_record.assert_not_called()  # type: ignore

    @patch(
        'ddns.get_public_ip',
        side_effect=ddns.requests.exceptions.RequestException(
            "Connection failed"
        )
    )
    @patch('ddns.get_dns_records')
    @patch('ddns.get_zone_id', return_value='fake-zone-id')
    def test_main_network_error_returns_3(
        self,
        _mock_get_zone_id,
        _mock_get_dns_records,
        mock_get_public_ip
    ):
        """Verify main() returns exit code 3 on a network error."""
        # Arrange: Mocks are set up. get_public_ip will raise an exception.

        # Act: Run the main function.
        with patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()

        # Assert
        self.assertEqual(exit_code, 3)
        # Ensure we tried to get the IP, which is where the error occurs
        mock_get_public_ip.assert_called_once()  # type: ignore

    @patch('ddns.requests.patch')  # Patch the underlying requests.patch call
    @patch('ddns.get_public_ip', return_value='192.0.2.100')
    @patch('ddns.get_dns_records')
    @patch('ddns.get_zone_id', return_value='fake-zone-id')
    def test_main_dry_run_does_not_update(
        self, _mock_get_zone_id, mock_get_dns_records, _mock_get_public_ip, mock_requests_patch
    ):
        """Verify main() does not attempt a real update when DRY_RUN is active."""
        # Arrange: Set DDNS_DRY_RUN to '1' to enable dry-run mode.
        # We need to reload the module for the module-level DRY_RUN constant to update.
        os.environ['DDNS_DRY_RUN'] = '1'
        reload(ddns)
        mock_get_dns_records.return_value = [
            {'id': 'rec-123', 'name': 'host.example.com', 'content': '192.0.2.1'}
        ]

        # Act: Run the main function.
        with patch.object(sys, 'argv', ['ddns.py']):
            exit_code = ddns.main()

        # Assert
        self.assertEqual(exit_code, 0, "Exit code should be 0 for a successful dry-run update.")
        # Verify that the underlying `requests.patch` function was NEVER called.
        mock_requests_patch.assert_not_called()

        # Cleanup: Restore DDNS_DRY_RUN to its original state for other tests
        os.environ['DDNS_DRY_RUN'] = '0'
        reload(ddns)
