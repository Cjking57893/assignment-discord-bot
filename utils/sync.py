"""Canvas data synchronization utilities."""

from canvas_api.endpoints import get_courses, get_assignments
from database.db_manager import upsert_courses, upsert_assignments, init_db


async def sync_canvas_data() -> None:
    """Fetch all courses and assignments from Canvas and store in local database."""
    print("Syncing Canvas data...")
    
    # Ensure DB exists
    await init_db()
    
    # Fetch and store courses
    courses = get_courses()
    await upsert_courses(courses)

    # Fetch and store assignments for each course
    for course in courses:
        course_id = course["id"]
        assignments = get_assignments(course_id)
        await upsert_assignments(assignments, course_id)

    print("Canvas data synced successfully.")
