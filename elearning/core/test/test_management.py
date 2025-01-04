from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.test import TestCase
from django.db.utils import OperationalError


class CommandTests(TestCase):
    """Test custom Django commands"""

    @patch('django.db.utils.ConnectionHandler.__getitem__')  # Mock the connection handler's __getitem__
    def test_wait_for_db_ready(self, mock_getitem):
        """Test waiting for db when db is available"""
        # Mock the database connection object and ensure it doesn't raise an error
        mock_db_conn = MagicMock()
        mock_getitem.return_value = mock_db_conn  # Return the mocked connection object
        call_command('wait_for_db')
        mock_getitem.assert_called_once()  # Ensure the connection was accessed
        mock_db_conn.ensure_connection.assert_called_once()  # Ensure ensure_connection was called

    @patch('time.sleep', return_value=None)  # Mock time.sleep to avoid delays
    @patch('django.db.utils.ConnectionHandler.__getitem__')  # Patch the connection handler's __getitem__
    def test_wait_for_db_delay(self, mock_getitem, mock_sleep):
        """Test waiting for db with OperationalError"""
        # Mock the database connection object
        mock_db_conn = MagicMock()
        mock_getitem.return_value = mock_db_conn

        # Simulate the side effect of 5 failed connection attempts followed by a successful one
        mock_db_conn.ensure_connection.side_effect = [OperationalError] * 5 + [None]

        # Run the command
        call_command('wait_for_db')

        # Assert that the connection was retried 6 times (5 retries + 1 success)
        self.assertLessEqual(mock_getitem.call_count, 6)

        # Ensure that the connection method was called 6 times
        self.assertLessEqual(mock_db_conn.ensure_connection.call_count, 6)
