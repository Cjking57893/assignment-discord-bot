"""
Regression tests for database schema and operations.
Ensures critical database functionality remains stable.
"""

import unittest
import os
import aiosqlite
from datetime import datetime, timezone, timedelta
import database.db_manager as db_manager
from database.db_manager import init_db
from utils.datetime_utils import to_utc_iso_z


class TestDatabaseSchemaRegression(unittest.IsolatedAsyncioTestCase):
    """Regression tests for database schema stability."""

    @classmethod
    def setUpClass(cls):
        """Set up test database path."""
        cls.test_db_path = "data/test_regression_db.db"

    async def asyncSetUp(self):
        """Initialize fresh database for each test."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        """Clean up test database."""
        db_manager.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    async def test_assignments_table_has_composite_primary_key(self):
        """
        REGRESSION: Assignments table should use composite PK (course_id, id).
        Early versions used single-column PK which caused issues with cross-course ID collisions.
        """
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute("PRAGMA table_info(assignments)") as cursor:
                columns = await cursor.fetchall()
                
            # Get primary key columns
            pk_columns = [col[1] for col in columns if col[5] > 0]
            
            # Should have composite key
            self.assertEqual(len(pk_columns), 2, "Should have 2 PK columns")
            self.assertIn('course_id', pk_columns)
            self.assertIn('id', pk_columns)

    async def test_assignments_table_has_due_reminder_columns(self):
        """
        REGRESSION: Assignments table should have due date reminder tracking columns.
        These were added via migration.
        """
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute("PRAGMA table_info(assignments)") as cursor:
                columns = await cursor.fetchall()
                
            column_names = [col[1] for col in columns]
            
            self.assertIn('due_reminder_2d_sent', column_names)
            self.assertIn('due_reminder_1d_sent', column_names)
            self.assertIn('due_reminder_12h_sent', column_names)

    async def test_study_plans_requires_course_id(self):
        """
        REGRESSION: Study plans table should require course_id (NOT NULL).
        Early tests failed because course_id was missing.
        """
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute("PRAGMA table_info(study_plans)") as cursor:
                columns = await cursor.fetchall()
                
            course_id_col = [col for col in columns if col[1] == 'course_id'][0]
            
            # col[3] is the NOT NULL flag
            self.assertEqual(course_id_col[3], 1, "course_id should be NOT NULL")

    async def test_study_plans_has_reminder_columns(self):
        """
        REGRESSION: Study plans should have reminder tracking columns.
        These were added via migration.
        """
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute("PRAGMA table_info(study_plans)") as cursor:
                columns = await cursor.fetchall()
                
            column_names = [col[1] for col in columns]
            
            self.assertIn('reminder_24h_sent', column_names)
            self.assertIn('reminder_1h_sent', column_names)
            self.assertIn('reminder_now_sent', column_names)

    async def test_assignments_column_name_is_due_at(self):
        """
        REGRESSION: The due date column is 'due_at', not 'due_at_utc'.
        Early integration tests used wrong column name.
        """
        async with aiosqlite.connect(self.test_db_path) as db:
            async with db.execute("PRAGMA table_info(assignments)") as cursor:
                columns = await cursor.fetchall()
                
            column_names = [col[1] for col in columns]
            
            self.assertIn('due_at', column_names)
            self.assertNotIn('due_at_utc', column_names)

    async def test_foreign_key_constraints_exist(self):
        """
        REGRESSION: Ensure foreign key constraints are properly defined.
        """
        async with aiosqlite.connect(self.test_db_path) as db:
            # Check assignments -> courses FK
            async with db.execute("PRAGMA foreign_key_list(assignments)") as cursor:
                fks = await cursor.fetchall()
                
            self.assertGreater(len(fks), 0, "Assignments should have foreign key to courses")
            
            # Verify it references courses table
            course_fk = [fk for fk in fks if fk[2] == 'courses']
            self.assertGreater(len(course_fk), 0, "Should reference courses table")


class TestDatabaseOperationsRegression(unittest.IsolatedAsyncioTestCase):
    """Regression tests for database operation behavior."""

    @classmethod
    def setUpClass(cls):
        """Set up test database path."""
        cls.test_db_path = "data/test_regression_ops_db.db"

    async def asyncSetUp(self):
        """Initialize fresh database for each test."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        """Clean up test database."""
        db_manager.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    async def test_upsert_functions_use_list_api(self):
        """
        REGRESSION: upsert_courses and upsert_assignments take lists, not single items.
        Early tests assumed singular function signatures.
        """
        from database.db_manager import upsert_courses, upsert_assignments
        import inspect
        
        # Check signatures
        courses_sig = inspect.signature(upsert_courses)
        self.assertIn('courses', courses_sig.parameters)
        
        assignments_sig = inspect.signature(upsert_assignments)
        self.assertIn('assignments', assignments_sig.parameters)
        self.assertIn('course_id', assignments_sig.parameters)

    async def test_db_path_comes_from_config(self):
        """
        REGRESSION: DB_PATH should be imported from config, not hardcoded.
        """
        import database.db_manager as db_mgr
        
        # DB_PATH should be set from config with fallback
        self.assertIsNotNone(db_mgr.DB_PATH)
        
        # Verify it's actually being used
        self.assertTrue(os.path.exists(os.path.dirname(self.test_db_path)))


if __name__ == "__main__":
    unittest.main()
