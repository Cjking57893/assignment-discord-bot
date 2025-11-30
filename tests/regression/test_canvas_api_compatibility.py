"""
Regression tests for Canvas API compatibility.
Ensures API client continues to work with Canvas API responses.
"""

import unittest
from unittest.mock import Mock, patch
from canvas_api.client import CanvasClient
from canvas_api.endpoints import get_courses, get_assignments


class TestCanvasAPIRegression(unittest.TestCase):
    """Regression tests for Canvas API behavior."""

    def test_client_handles_pagination_link_header(self):
        """
        REGRESSION: Client should parse Link header for pagination.
        Canvas uses RFC 5988 Link headers with rel="next".
        """
        client = CanvasClient(base_url="https://test.canvas.com", token="test")
        
        with patch('canvas_api.client.requests.get') as mock_get:
            # First page
            mock_response1 = Mock()
            mock_response1.json.return_value = [{"id": 1}]
            mock_response1.headers.get.return_value = '<https://test.canvas.com/api/v1/courses?page=2>; rel="next"'
            
            # Second page
            mock_response2 = Mock()
            mock_response2.json.return_value = [{"id": 2}]
            mock_response2.headers.get.return_value = ""
            
            mock_get.side_effect = [mock_response1, mock_response2]
            
            result = client.get("courses")
            
            self.assertEqual(len(result), 2)
            self.assertEqual(mock_get.call_count, 2)

    def test_client_sets_per_page_parameter(self):
        """
        REGRESSION: Client should automatically add per_page=100 for efficiency.
        """
        client = CanvasClient(base_url="https://test.canvas.com", token="test")
        
        with patch('canvas_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.headers.get.return_value = ""
            mock_get.return_value = mock_response
            
            client.get("courses")
            
            call_kwargs = mock_get.call_args.kwargs
            self.assertEqual(call_kwargs['params']['per_page'], 100)

    def test_client_includes_auth_header(self):
        """
        REGRESSION: Client should include Bearer token in Authorization header.
        """
        client = CanvasClient(base_url="https://test.canvas.com", token="test_token_123")
        
        self.assertIn("Authorization", client.headers)
        self.assertEqual(client.headers["Authorization"], "Bearer test_token_123")

    def test_endpoints_filter_malformed_courses(self):
        """
        REGRESSION: get_courses should filter out courses without names.
        Canvas can return incomplete data.
        """
        with patch('canvas_api.endpoints.canvas_client.get') as mock_get:
            mock_get.return_value = [
                {"id": 1, "name": "Valid Course"},
                {"id": 2},  # Missing name - should be filtered
                {"id": 3, "name": "Another Valid"}
            ]
            
            result = get_courses()
            
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["id"], 1)
            self.assertEqual(result[1]["id"], 3)

    def test_endpoints_filter_malformed_assignments(self):
        """
        REGRESSION: get_assignments should filter assignments without id or name.
        """
        with patch('canvas_api.endpoints.canvas_client.get') as mock_get:
            mock_get.return_value = [
                {"id": 1, "name": "Valid"},
                {"id": 2},  # Missing name
                {"name": "Missing ID"},  # Missing id
                {"id": 3, "name": "Valid Too"}
            ]
            
            result = get_assignments(101)
            
            self.assertEqual(len(result), 2)

    def test_assignments_default_has_submitted_to_false(self):
        """
        REGRESSION: has_submitted_submissions should default to False if missing.
        """
        with patch('canvas_api.endpoints.canvas_client.get') as mock_get:
            mock_get.return_value = [
                {"id": 1, "name": "Assignment"}
                # has_submitted_submissions missing
            ]
            
            result = get_assignments(101)
            
            self.assertEqual(result[0]["has_submitted_submissions"], False)

    def test_courses_handle_missing_optional_fields(self):
        """
        REGRESSION: Optional course fields should default to None.
        """
        with patch('canvas_api.endpoints.canvas_client.get') as mock_get:
            mock_get.return_value = [
                {"id": 1, "name": "Minimal Course"}
                # course_code, start_at, end_at missing
            ]
            
            result = get_courses()
            
            self.assertIsNone(result[0]["course_code"])
            self.assertIsNone(result[0]["start_at"])
            self.assertIsNone(result[0]["end_at"])

    def test_client_handles_single_object_response(self):
        """
        REGRESSION: Client should handle non-list responses (single objects).
        """
        client = CanvasClient(base_url="https://test.canvas.com", token="test")
        
        with patch('canvas_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"id": 123, "name": "Single Course"}
            mock_response.headers.get.return_value = ""
            mock_get.return_value = mock_response
            
            result = client.get("courses/123")
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result["id"], 123)

    def test_client_has_request_timeout(self):
        """
        REGRESSION: Client should set reasonable timeout to prevent hanging.
        """
        client = CanvasClient(base_url="https://test.canvas.com", token="test")
        
        with patch('canvas_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.headers.get.return_value = ""
            mock_get.return_value = mock_response
            
            client.get("courses")
            
            call_kwargs = mock_get.call_args.kwargs
            self.assertIn('timeout', call_kwargs)
            self.assertGreater(call_kwargs['timeout'], 0)


if __name__ == "__main__":
    unittest.main()
