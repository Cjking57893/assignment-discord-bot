"""
Acceptance tests for core user workflows.
Tests end-to-end scenarios from a user's perspective.
"""

import unittest
import os
from datetime import datetime, timezone, timedelta
import database.db_manager as db_manager
from database.db_manager import (
    init_db, upsert_courses, upsert_assignments,
    upsert_study_plan, get_user_plans_for_week_detailed,
    set_assignment_completed, get_week_assignments_with_status
)
from utils.datetime_utils import to_utc_iso_z


class TestStudentWeeklyPlanningWorkflow(unittest.IsolatedAsyncioTestCase):
    """
    User Story: As a student, I want to plan my weekly study sessions
    so that I can stay organized and complete assignments on time.
    
    Acceptance Criteria:
    - Student can view assignments for the week
    - Student can schedule study sessions at specific times
    - Student can add notes to their study plans
    - Student can view all planned sessions for the week
    """

    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "data/test_acceptance_workflow.db"

    async def asyncSetUp(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        db_manager.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    async def test_student_plans_weekly_study_sessions(self):
        """
        SCENARIO: Student receives assignments and plans study sessions
        
        GIVEN Sarah is taking CS 101 and has 3 assignments due this week
        WHEN she creates a weekly study plan
        THEN she should be able to schedule sessions for each assignment
        AND add notes about what to study
        AND view her complete weekly schedule
        """
        # Setup - Sarah's courses and assignments
        await upsert_courses([{
            "id": 101,
            "name": "Introduction to Programming",
            "course_code": "CS101"
        }])
        
        monday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        monday = monday - timedelta(days=monday.weekday())
        
        await upsert_assignments([
            {
                "id": 1001,
                "name": "Homework 1 - Variables",
                "due_at": to_utc_iso_z(monday + timedelta(days=3, hours=23, minutes=59)),
                "has_submitted_submissions": False
            },
            {
                "id": 1002,
                "name": "Quiz 1 - Control Flow",
                "due_at": to_utc_iso_z(monday + timedelta(days=4, hours=23, minutes=59)),
                "has_submitted_submissions": False
            },
            {
                "id": 1003,
                "name": "Lab 1 - Functions",
                "due_at": to_utc_iso_z(monday + timedelta(days=5, hours=23, minutes=59)),
                "has_submitted_submissions": False
            }
        ], 101)
        
        # Sarah plans her study sessions
        await upsert_study_plan(
            user_id="sarah_student",
            course_id=101,
            assignment_id=1001,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=1, hours=14)),  # Tuesday 2 PM
            notes="Review chapter 2 on variables and data types"
        )
        
        await upsert_study_plan(
            user_id="sarah_student",
            course_id=101,
            assignment_id=1002,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=2, hours=15)),  # Wednesday 3 PM
            notes="Practice if/else and loops from slides"
        )
        
        await upsert_study_plan(
            user_id="sarah_student",
            course_id=101,
            assignment_id=1003,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=4, hours=10)),  # Friday 10 AM
            notes="Complete lab exercises on functions"
        )
        
        # Sarah views her weekly plan
        plans = await get_user_plans_for_week_detailed("sarah_student", monday)
        
        # Verify all three sessions are planned
        self.assertEqual(len(plans), 3, "Should have 3 planned study sessions")
        
        # Verify assignments are present
        assignment_names = [plan[4] for plan in plans]  # assignment_name is index 4
        self.assertIn("Homework 1 - Variables", assignment_names)
        self.assertIn("Quiz 1 - Control Flow", assignment_names)
        self.assertIn("Lab 1 - Functions", assignment_names)
        
        # Verify notes are preserved
        notes_list = [plan[3] for plan in plans]  # notes is index 3
        self.assertIn("Review chapter 2 on variables and data types", str(notes_list))


class TestAssignmentCompletionWorkflow(unittest.IsolatedAsyncioTestCase):
    """
    User Story: As a student, I want to track my assignment completion
    so that I know what I've finished and what remains.
    
    Acceptance Criteria:
    - Student can mark assignments as complete
    - Student can see completion status for all assignments
    - Completed assignments are clearly distinguished from incomplete ones
    - Student can track progress throughout the week
    """

    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "data/test_acceptance_completion.db"

    async def asyncSetUp(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        db_manager.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    async def test_student_tracks_assignment_completion(self):
        """
        SCENARIO: Student completes assignments throughout the week
        
        GIVEN Michael has 4 assignments this week
        WHEN he completes them one by one
        THEN he should be able to mark each as complete
        AND see his progress
        AND know which assignments remain
        """
        # Setup - Michael's assignments
        await upsert_courses([{
            "id": 201,
            "name": "Data Structures",
            "course_code": "CS201"
        }])
        
        monday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        monday = monday - timedelta(days=monday.weekday())
        
        assignments = [
            {"id": 2001, "name": "Assignment 1", "due_at": to_utc_iso_z(monday + timedelta(days=2)), "has_submitted_submissions": False},
            {"id": 2002, "name": "Assignment 2", "due_at": to_utc_iso_z(monday + timedelta(days=3)), "has_submitted_submissions": False},
            {"id": 2003, "name": "Assignment 3", "due_at": to_utc_iso_z(monday + timedelta(days=4)), "has_submitted_submissions": False},
            {"id": 2004, "name": "Assignment 4", "due_at": to_utc_iso_z(monday + timedelta(days=5)), "has_submitted_submissions": False}
        ]
        await upsert_assignments(assignments, 201)
        
        # Michael creates study plans for all
        for i, assign in enumerate(assignments):
            await upsert_study_plan(
                user_id="michael_student",
                course_id=201,
                assignment_id=assign["id"],
                planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=i)),
                notes=f"Work on {assign['name']}"
            )
        
        # Initially, nothing is complete
        week_status = await get_week_assignments_with_status("michael_student", monday)
        completed_count = sum(1 for row in week_status if row[6] == 1)
        self.assertEqual(completed_count, 0, "Initially no assignments should be complete")
        
        # Michael completes first two assignments
        await set_assignment_completed("michael_student", 201, 2001, True)
        await set_assignment_completed("michael_student", 201, 2002, True)
        
        # Check progress
        week_status = await get_week_assignments_with_status("michael_student", monday)
        completed_count = sum(1 for row in week_status if row[6] == 1)
        incomplete_count = sum(1 for row in week_status if row[6] == 0)
        
        self.assertEqual(completed_count, 2, "Should have 2 completed assignments")
        self.assertEqual(incomplete_count, 2, "Should have 2 incomplete assignments")
        self.assertEqual(len(week_status), 4, "Should have 4 total assignments")


class TestMultiCourseManagement(unittest.IsolatedAsyncioTestCase):
    """
    User Story: As a student taking multiple courses, I want to manage
    assignments across all my classes in one place.
    
    Acceptance Criteria:
    - Student can view assignments from all courses
    - Student can plan sessions across different courses
    - Each course's assignments are clearly identified
    - Student can track completion per course
    """

    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "data/test_acceptance_multi_course.db"

    async def asyncSetUp(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        db_manager.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    async def test_student_manages_multiple_courses(self):
        """
        SCENARIO: Student manages assignments from 3 different courses
        
        GIVEN Emma is taking CS, Math, and Physics
        WHEN she views her weekly assignments
        THEN she should see assignments from all three courses
        AND be able to plan sessions for each
        AND track completion separately per course
        """
        # Setup - Emma's three courses
        await upsert_courses([
            {"id": 301, "name": "Computer Science", "course_code": "CS101"},
            {"id": 302, "name": "Calculus I", "course_code": "MATH101"},
            {"id": 303, "name": "Physics I", "course_code": "PHYS101"}
        ])
        
        monday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        monday = monday - timedelta(days=monday.weekday())
        
        # CS assignment
        await upsert_assignments([
            {"id": 3001, "name": "Programming Project", "due_at": to_utc_iso_z(monday + timedelta(days=3)), "has_submitted_submissions": False}
        ], 301)
        
        # Math assignment
        await upsert_assignments([
            {"id": 3002, "name": "Problem Set 5", "due_at": to_utc_iso_z(monday + timedelta(days=4)), "has_submitted_submissions": False}
        ], 302)
        
        # Physics assignment
        await upsert_assignments([
            {"id": 3003, "name": "Lab Report", "due_at": to_utc_iso_z(monday + timedelta(days=5)), "has_submitted_submissions": False}
        ], 303)
        
        # Emma plans sessions for all three courses
        await upsert_study_plan(
            user_id="emma_student",
            course_id=301,
            assignment_id=3001,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=1, hours=14)),
            notes="Code the main algorithm"
        )
        
        await upsert_study_plan(
            user_id="emma_student",
            course_id=302,
            assignment_id=3002,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=2, hours=16)),
            notes="Practice derivatives"
        )
        
        await upsert_study_plan(
            user_id="emma_student",
            course_id=303,
            assignment_id=3003,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=3, hours=10)),
            notes="Write analysis section"
        )
        
        # Emma views her weekly plan
        plans = await get_user_plans_for_week_detailed("emma_student", monday)
        
        # Should have all three courses represented
        self.assertEqual(len(plans), 3, "Should have 3 planned sessions across 3 courses")
        
        # Verify courses are distinct
        course_codes = set(plan[6] for plan in plans)  # course_code
        self.assertEqual(len(course_codes), 3, "Should have 3 different courses")
        
        # Emma completes the CS assignment
        await set_assignment_completed("emma_student", 301, 3001, True)
        
        # Check status across all courses
        week_status = await get_week_assignments_with_status("emma_student", monday)
        
        # Find the completed assignment
        completed_assignments = [row for row in week_status if row[6] == 1]
        self.assertEqual(len(completed_assignments), 1)
        self.assertEqual(completed_assignments[0][0], 3001)  # CS assignment ID


class TestUserIsolation(unittest.IsolatedAsyncioTestCase):
    """
    User Story: As a student, my data should be separate from other students
    so that my plans and completion status are private.
    
    Acceptance Criteria:
    - Each student only sees their own study plans
    - Each student's completion status is independent
    - Students can work on the same assignments without interference
    """

    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "data/test_acceptance_isolation.db"

    async def asyncSetUp(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = self.test_db_path
        await init_db()

    async def asyncTearDown(self):
        db_manager.DB_PATH = self.original_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    async def test_multiple_students_data_isolation(self):
        """
        SCENARIO: Multiple students in the same class work independently
        
        GIVEN Alex and Jordan are both in CS101
        WHEN they each plan sessions for the same assignment
        THEN their plans should be completely separate
        AND their completion statuses should be independent
        """
        # Setup - Shared course and assignment
        await upsert_courses([{
            "id": 401,
            "name": "Shared Course",
            "course_code": "CS101"
        }])
        
        monday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        monday = monday - timedelta(days=monday.weekday())
        
        await upsert_assignments([
            {"id": 4001, "name": "Shared Assignment", "due_at": to_utc_iso_z(monday + timedelta(days=5)), "has_submitted_submissions": False}
        ], 401)
        
        # Alex plans to work on Wednesday
        await upsert_study_plan(
            user_id="alex",
            course_id=401,
            assignment_id=4001,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=2, hours=10)),
            notes="Alex's plan: Start early"
        )
        
        # Jordan plans to work on Friday
        await upsert_study_plan(
            user_id="jordan",
            course_id=401,
            assignment_id=4001,
            planned_at_iso_utc=to_utc_iso_z(monday + timedelta(days=4, hours=18)),
            notes="Jordan's plan: Finish before deadline"
        )
        
        # Each student sees only their own plan
        alex_plans = await get_user_plans_for_week_detailed("alex", monday)
        jordan_plans = await get_user_plans_for_week_detailed("jordan", monday)
        
        self.assertEqual(len(alex_plans), 1, "Alex should have 1 plan")
        self.assertEqual(len(jordan_plans), 1, "Jordan should have 1 plan")
        
        # Alex completes the assignment
        await set_assignment_completed("alex", 401, 4001, True)
        
        # Check completion status
        alex_status = await get_week_assignments_with_status("alex", monday)
        jordan_status = await get_week_assignments_with_status("jordan", monday)
        
        # Alex: completed, Jordan: not completed
        self.assertEqual(alex_status[0][6], 1, "Alex's should be completed")
        self.assertEqual(jordan_status[0][6], 0, "Jordan's should not be completed")


if __name__ == "__main__":
    unittest.main()
