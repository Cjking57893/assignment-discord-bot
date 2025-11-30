"""
Integration tests for Canvas sync functionality.
Tests the complete sync workflow from API to database.
"""

import unittest
import os
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
import aiosqlite
from utils.sync import sync_canvas_data
from database.db_manager import init_db
from utils.datetime_utils import to_utc_iso_z


class TestSyncIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for Canvas data synchronization."""

    @classmethod
    def setUpClass(cls):
        """Set up test database path."""
        cls.test_db_path = "data/test_sync_bot.db"

    async def asyncSetUp(self):
        """Initialize fresh database for each test."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        import database.db_manager as db_manager
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = self.test_db_path
        
        await init_db()

    async def asyncTearDown(self):
        """Clean up test database."""
        import database.db_manager as db_manager
        db_manager.DB_PATH = self.original_db_path
        
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    @patch('utils.sync.get_courses')
    @patch('utils.sync.get_assignments')
    async def test_full_sync_workflow(self, mock_get_assignments, mock_get_courses):
        """Test complete sync from Canvas API to database."""
        # Mock Canvas API responses
        mock_get_courses.return_value = [
            {
                "id": 201,
                "name": "Advanced Python",
                "course_code": "CS301",
                "start_at": "2025-01-10T00:00:00Z",
                "end_at": "2025-05-20T00:00:00Z"
            },
            {
                "id": 202,
                "name": "Machine Learning",
                "course_code": "CS401",
                "start_at": "2025-01-10T00:00:00Z",
                "end_at": "2025-05-20T00:00:00Z"
            }
        ]

        mock_get_assignments.side_effect = [
            # Assignments for course 201
            [
                {
                    "id": 1001,
                    "name": "Python Project 1",
                    "due_at": "2025-12-15T23:59:00Z",
                    "html_url": "https://canvas.com/courses/201/assignments/1001",
                    "has_submitted_submissions": False
                },
                {
                    "id": 1002,
                    "name": "Python Quiz 1",
                    "due_at": "2025-12-20T23:59:00Z",
                    "html_url": "https://canvas.com/courses/201/assignments/1002",
                    "has_submitted_submissions": False
                }
            ],
            # Assignments for course 202
            [
                {
                    "id": 2001,
                    "name": "ML Assignment 1",
                    "due_at": "2025-12-18T23:59:00Z",
                    "html_url": "https://canvas.com/courses/202/assignments/2001",
                    "has_submitted_submissions": False
                }
            ]
        ]

        # Perform sync
        await sync_canvas_data()

        # Verify courses were synced
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM courses") as cursor:
                count = (await cursor.fetchone())[0]
                self.assertEqual(count, 2)

            # Verify assignments were synced
            async with db.execute("SELECT COUNT(*) FROM assignments") as cursor:
                count = (await cursor.fetchone())[0]
                self.assertEqual(count, 3)

            # Verify course details
            async with db.execute(
                "SELECT name, course_code FROM courses WHERE id = ?",
                (201,)
            ) as cursor:
                row = await cursor.fetchone()
                self.assertEqual(row[0], "Advanced Python")
                self.assertEqual(row[1], "CS301")

            # Verify assignment relationships
            async with db.execute(
                "SELECT COUNT(*) FROM assignments WHERE course_id = ?",
                (201,)
            ) as cursor:
                count = (await cursor.fetchone())[0]
                self.assertEqual(count, 2)

    @patch('utils.sync.get_courses')
    @patch('utils.sync.get_assignments')
    async def test_sync_updates_existing_data(self, mock_get_assignments, mock_get_courses):
        """Test that sync updates existing courses and assignments."""
        # First sync
        mock_get_courses.return_value = [
            {
                "id": 301,
                "name": "Data Science",
                "course_code": "DS101",
                "start_at": "2025-01-10T00:00:00Z",
                "end_at": "2025-05-20T00:00:00Z"
            }
        ]

        mock_get_assignments.return_value = [
            {
                "id": 3001,
                "name": "Initial Assignment",
                "due_at": "2025-12-10T23:59:00Z",
                "html_url": "https://canvas.com/courses/301/assignments/3001",
                "has_submitted_submissions": False
            }
        ]

        await sync_canvas_data()

        # Verify initial data
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute(
                "SELECT name FROM assignments WHERE id = ?",
                (3001,)
            ) as cursor:
                row = await cursor.fetchone()
                self.assertEqual(row[0], "Initial Assignment")

        # Second sync with updated data
        mock_get_assignments.return_value = [
            {
                "id": 3001,
                "name": "Updated Assignment",  # Name changed
                "due_at": "2025-12-15T23:59:00Z",  # Due date changed
                "html_url": "https://canvas.com/courses/301/assignments/3001",
                "has_submitted_submissions": False
            }
        ]

        await sync_canvas_data()

        # Verify data was updated
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute(
                "SELECT name, due_at FROM assignments WHERE id = ?",
                (3001,)
            ) as cursor:
                row = await cursor.fetchone()
                self.assertEqual(row[0], "Updated Assignment")
                self.assertIn("2025-12-15", row[1])

    @patch('utils.sync.get_courses')
    @patch('utils.sync.get_assignments')
    async def test_sync_handles_no_assignments(self, mock_get_assignments, mock_get_courses):
        """Test sync when a course has no assignments."""
        mock_get_courses.return_value = [
            {
                "id": 401,
                "name": "Empty Course",
                "course_code": "EMPTY101",
                "start_at": "2025-01-10T00:00:00Z",
                "end_at": "2025-05-20T00:00:00Z"
            }
        ]

        mock_get_assignments.return_value = []

        # Should not raise an error
        await sync_canvas_data()

        # Verify course was created
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM courses WHERE id = ?",
                (401,)
            ) as cursor:
                count = (await cursor.fetchone())[0]
                self.assertEqual(count, 1)

            # Verify no assignments
            async with db.execute(
                "SELECT COUNT(*) FROM assignments WHERE course_id = ?",
                (401,)
            ) as cursor:
                count = (await cursor.fetchone())[0]
                self.assertEqual(count, 0)

    @patch('utils.sync.get_courses')
    @patch('utils.sync.get_assignments')
    async def test_sync_preserves_user_data(self, mock_get_assignments, mock_get_courses):
        """Test that sync doesn't affect user-specific data like study plans."""
        # Setup initial data
        mock_get_courses.return_value = [
            {
                "id": 501,
                "name": "Test Course",
                "course_code": "TEST501",
                "start_at": "2025-01-10T00:00:00Z",
                "end_at": "2025-05-20T00:00:00Z"
            }
        ]

        mock_get_assignments.return_value = [
            {
                "id": 5001,
                "name": "Test Assignment",
                "due_at": "2025-12-25T23:59:00Z",
                "html_url": "https://canvas.com/courses/501/assignments/5001",
                "has_submitted_submissions": False
            }
        ]

        await sync_canvas_data()

        # Add user study plan
        async with aiosqlite.connect(self.test_db_path) as db:
            planned_time = datetime.now(timezone.utc) + timedelta(days=5)
            await db.execute("""
                INSERT INTO study_plans (user_id, course_id, assignment_id, planned_at_utc, notes)
                VALUES (?, ?, ?, ?, ?)
            """, ("test_user", 5000, 5001, to_utc_iso_z(planned_time), "My study plan"))
            await db.commit()

        # Perform another sync
        await sync_canvas_data()

        # Verify study plan still exists
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM study_plans WHERE user_id = ?",
                ("test_user",)
            ) as cursor:
                count = (await cursor.fetchone())[0]
                self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
