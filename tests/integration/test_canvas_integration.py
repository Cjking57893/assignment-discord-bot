"""
Integration tests for Canvas API client and endpoints.
Tests the complete flow of fetching and processing Canvas data.
"""

import unittest
from unittest.mock import Mock, patch
from canvas_api.client import CanvasClient
from canvas_api.endpoints import get_courses, get_assignments


class TestCanvasIntegration(unittest.TestCase):
    """Integration tests for Canvas API components."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = CanvasClient(
            base_url="https://test.canvas.com",
            token="test_token"
        )

    @patch('canvas_api.client.requests.get')
    def test_fetch_courses_and_assignments_flow(self, mock_get):
        """Test complete flow: fetch courses, then fetch assignments for each."""
        # Mock courses response
        courses_response = Mock()
        courses_response.json.return_value = [
            {
                "id": 101,
                "name": "Introduction to Python",
                "course_code": "CS101"
            },
            {
                "id": 102,
                "name": "Data Structures",
                "course_code": "CS201"
            }
        ]
        courses_response.headers.get.return_value = ""

        # Mock assignments response for course 101
        assignments_response = Mock()
        assignments_response.json.return_value = [
            {
                "id": 1001,
                "name": "Homework 1",
                "due_at": "2025-12-15T23:59:00Z",
                "html_url": "https://canvas.com/courses/101/assignments/1001",
                "has_submitted_submissions": False
            }
        ]
        assignments_response.headers.get.return_value = ""

        mock_get.side_effect = [courses_response, assignments_response]

        # Fetch courses
        courses = self.client.get("courses")
        self.assertEqual(len(courses), 2)
        self.assertEqual(courses[0]["id"], 101)

        # Fetch assignments for first course
        assignments = self.client.get(f"courses/{courses[0]['id']}/assignments")
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["name"], "Homework 1")

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_courses_to_assignments_pipeline(self, mock_get):
        """Test the full pipeline from courses to assignments."""
        # Setup mock for courses
        mock_get.return_value = [
            {"id": 123, "name": "Test Course", "course_code": "TEST101"}
        ]

        # Get courses
        courses = get_courses()
        self.assertEqual(len(courses), 1)
        course_id = courses[0]["id"]

        # Setup mock for assignments
        mock_get.return_value = [
            {
                "id": 1,
                "name": "Assignment 1",
                "due_at": "2025-12-20T23:59:00Z",
                "html_url": "https://test.com/assignments/1",
                "has_submitted_submissions": False
            },
            {
                "id": 2,
                "name": "Assignment 2",
                "due_at": None,
                "html_url": "https://test.com/assignments/2",
                "has_submitted_submissions": True
            }
        ]

        # Get assignments
        assignments = get_assignments(course_id)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0]["id"], 1)
        self.assertEqual(assignments[1]["has_submitted_submissions"], True)

    @patch('canvas_api.client.requests.get')
    def test_pagination_with_real_data_structure(self, mock_get):
        """Test pagination handling with realistic multi-page data."""
        # Page 1
        page1_response = Mock()
        page1_response.json.return_value = [
            {"id": i, "name": f"Course {i}", "course_code": f"C{i}"}
            for i in range(1, 101)
        ]
        page1_response.headers.get.return_value = '<https://test.canvas.com/courses?page=2>; rel="next"'

        # Page 2
        page2_response = Mock()
        page2_response.json.return_value = [
            {"id": i, "name": f"Course {i}", "course_code": f"C{i}"}
            for i in range(101, 151)
        ]
        page2_response.headers.get.return_value = ""

        mock_get.side_effect = [page1_response, page2_response]

        # Fetch all courses
        courses = self.client.get("courses")

        # Verify all pages were fetched
        self.assertEqual(len(courses), 150)
        self.assertEqual(courses[0]["id"], 1)
        self.assertEqual(courses[99]["id"], 100)
        self.assertEqual(courses[100]["id"], 101)
        self.assertEqual(courses[149]["id"], 150)

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_filter_and_process_course_data(self, mock_get):
        """Test that malformed data is filtered correctly in the pipeline."""
        mock_get.return_value = [
            {"id": 1, "name": "Valid Course"},
            {"id": 2},  # Missing name - should be filtered
            {"id": 3, "name": "Another Valid"},
            {},  # Missing both - should be filtered
        ]

        courses = get_courses()

        # Only valid courses should be returned
        self.assertEqual(len(courses), 2)
        self.assertEqual(courses[0]["id"], 1)
        self.assertEqual(courses[1]["id"], 3)

    @patch('canvas_api.endpoints.canvas_client.get')
    def test_assignment_data_normalization(self, mock_get):
        """Test that assignment data is normalized with defaults."""
        mock_get.return_value = [
            {
                "id": 1,
                "name": "Complete Assignment"
                # All optional fields present
            },
            {
                "id": 2,
                "name": "Minimal Assignment",
                "due_at": "2025-12-25T23:59:00Z"
                # Some optional fields missing
            }
        ]

        assignments = get_assignments(123)

        # First assignment should have defaults
        self.assertIsNone(assignments[0]["due_at"])
        self.assertIsNone(assignments[0]["html_url"])
        self.assertEqual(assignments[0]["has_submitted_submissions"], False)

        # Second assignment should have provided values
        self.assertEqual(assignments[1]["due_at"], "2025-12-25T23:59:00Z")
        self.assertEqual(assignments[1]["has_submitted_submissions"], False)


if __name__ == "__main__":
    unittest.main()
