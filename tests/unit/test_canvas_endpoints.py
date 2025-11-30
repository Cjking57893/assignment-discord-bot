"""
Unit tests for Canvas API endpoints.
Tests course and assignment fetching with data validation.
"""

import unittest
from unittest.mock import Mock, patch
from canvas_api.endpoints import get_courses, get_assignments


class TestCanvasEndpoints(unittest.TestCase):
    """Test suite for Canvas API endpoint functions."""

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_get_courses_success(self, mock_get):
        """Test successful course retrieval."""
        mock_get.return_value = [
            {
                "id": 123,
                "name": "Introduction to Python",
                "course_code": "CS101",
                "start_at": "2025-01-15T00:00:00Z",
                "end_at": "2025-05-15T00:00:00Z"
            },
            {
                "id": 456,
                "name": "Data Structures",
                "course_code": "CS201"
            }
        ]

        result = get_courses()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 123)
        self.assertEqual(result[0]["name"], "Introduction to Python")
        self.assertEqual(result[0]["course_code"], "CS101")
        self.assertEqual(result[1]["id"], 456)

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_get_courses_filters_malformed(self, mock_get):
        """Test that courses without names are filtered out."""
        mock_get.return_value = [
            {"id": 123, "name": "Valid Course"},
            {"id": 456},  # Missing name
            {"id": 789, "name": "Another Valid Course"}
        ]

        result = get_courses()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 123)
        self.assertEqual(result[1]["id"], 789)

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_get_courses_handles_missing_fields(self, mock_get):
        """Test that optional fields default to None."""
        mock_get.return_value = [
            {
                "id": 123,
                "name": "Minimal Course"
                # Missing course_code, start_at, end_at
            }
        ]

        result = get_courses()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 123)
        self.assertEqual(result[0]["name"], "Minimal Course")
        self.assertIsNone(result[0]["course_code"])
        self.assertIsNone(result[0]["start_at"])
        self.assertIsNone(result[0]["end_at"])

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_get_assignments_success(self, mock_get):
        """Test successful assignment retrieval."""
        mock_get.return_value = [
            {
                "id": 1001,
                "name": "Homework 1",
                "due_at": "2025-10-20T23:59:00Z",
                "html_url": "https://canvas.com/courses/123/assignments/1001",
                "has_submitted_submissions": False
            },
            {
                "id": 1002,
                "name": "Quiz 1",
                "due_at": "2025-10-25T23:59:00Z",
                "html_url": "https://canvas.com/courses/123/assignments/1002",
                "has_submitted_submissions": True
            }
        ]

        result = get_assignments(123)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1001)
        self.assertEqual(result[0]["name"], "Homework 1")
        self.assertEqual(result[1]["has_submitted_submissions"], True)

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_get_assignments_filters_malformed(self, mock_get):
        """Test that assignments without id or name are filtered."""
        mock_get.return_value = [
            {"id": 1001, "name": "Valid Assignment"},
            {"id": 1002},  # Missing name
            {"name": "Missing ID"},  # Missing id
            {"id": 1003, "name": "Another Valid"}
        ]

        result = get_assignments(123)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1001)
        self.assertEqual(result[1]["id"], 1003)

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_get_assignments_handles_missing_fields(self, mock_get):
        """Test that optional fields default to appropriate values."""
        mock_get.return_value = [
            {
                "id": 1001,
                "name": "Minimal Assignment"
                # Missing due_at, html_url, has_submitted_submissions
            }
        ]

        result = get_assignments(123)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1001)
        self.assertEqual(result[0]["name"], "Minimal Assignment")
        self.assertIsNone(result[0]["due_at"])
        self.assertIsNone(result[0]["html_url"])
        self.assertEqual(result[0]["has_submitted_submissions"], False)

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_get_assignments_correct_endpoint(self, mock_get):
        """Test that correct endpoint is called."""
        mock_get.return_value = []

        get_assignments(456)

        mock_get.assert_called_once_with("courses/456/assignments")


if __name__ == "__main__":
    unittest.main()
