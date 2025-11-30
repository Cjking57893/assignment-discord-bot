"""
Unit tests for Canvas API client.
Tests HTTP request handling, pagination, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from canvas_api.client import CanvasClient


class TestCanvasClient(unittest.TestCase):
    """Test suite for CanvasClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = CanvasClient(base_url="https://test.canvas.com", token="test_token")

    def test_init_sets_base_url(self):
        """Test that initialization sets base URL correctly."""
        self.assertEqual(self.client.base_url, "https://test.canvas.com")

    def test_init_sets_headers(self):
        """Test that initialization sets authorization headers."""
        self.assertIn("Authorization", self.client.headers)
        self.assertEqual(self.client.headers["Authorization"], "Bearer test_token")
        self.assertEqual(self.client.headers["Content-Type"], "application/json")

    @patch('canvas_api.client.requests.get')
    def test_get_single_object(self, mock_get):
        """Test GET request returning a single object (non-list)."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 123, "name": "Test Course"}
        mock_response.headers.get.return_value = ""
        mock_get.return_value = mock_response

        result = self.client.get("courses/123")

        self.assertEqual(result, {"id": 123, "name": "Test Course"})
        mock_get.assert_called_once()

    @patch('canvas_api.client.requests.get')
    def test_get_list_no_pagination(self, mock_get):
        """Test GET request returning a list without pagination."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "Course 1"},
            {"id": 2, "name": "Course 2"}
        ]
        mock_response.headers.get.return_value = ""
        mock_get.return_value = mock_response

        result = self.client.get("courses")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[1]["id"], 2)

    @patch('canvas_api.client.requests.get')
    def test_get_with_pagination(self, mock_get):
        """Test GET request with pagination (multiple pages)."""
        # First page
        mock_response1 = Mock()
        mock_response1.json.return_value = [{"id": 1, "name": "Course 1"}]
        mock_response1.headers.get.return_value = '<https://test.canvas.com/courses?page=2>; rel="next"'

        # Second page
        mock_response2 = Mock()
        mock_response2.json.return_value = [{"id": 2, "name": "Course 2"}]
        mock_response2.headers.get.return_value = ""

        mock_get.side_effect = [mock_response1, mock_response2]

        result = self.client.get("courses")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[1]["id"], 2)
        self.assertEqual(mock_get.call_count, 2)

    @patch('canvas_api.client.requests.get')
    def test_get_default_per_page(self, mock_get):
        """Test that default per_page parameter is added."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.headers.get.return_value = ""
        mock_get.return_value = mock_response

        self.client.get("courses")

        # Check that per_page was added to params
        call_args = mock_get.call_args
        self.assertIn("params", call_args.kwargs)
        self.assertEqual(call_args.kwargs["params"]["per_page"], 100)

    @patch('canvas_api.client.requests.get')
    def test_get_custom_params(self, mock_get):
        """Test GET request with custom parameters."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.headers.get.return_value = ""
        mock_get.return_value = mock_response

        self.client.get("courses", params={"enrollment_state": "active"})

        call_args = mock_get.call_args
        self.assertIn("params", call_args.kwargs)
        self.assertEqual(call_args.kwargs["params"]["enrollment_state"], "active")
        self.assertEqual(call_args.kwargs["params"]["per_page"], 100)

    @patch('canvas_api.client.requests.get')
    def test_get_timeout_parameter(self, mock_get):
        """Test that timeout parameter is included in request."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.headers.get.return_value = ""
        mock_get.return_value = mock_response

        self.client.get("courses")

        call_args = mock_get.call_args
        self.assertEqual(call_args.kwargs.get("timeout"), 30)

    @patch('canvas_api.client.requests.get')
    def test_get_raises_for_status(self, mock_get):
        """Test that HTTP errors are raised."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            self.client.get("courses/999")


if __name__ == "__main__":
    unittest.main()
