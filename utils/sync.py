from canvas_api.endpoints import get_courses, get_assignments
from database.db_manager import upsert_courses, upsert_assignments
from database.db_manager import init_db

async def sync_canvas_data():
    """Fetch all courses and assignments from Canvas and store them locally."""
    print("🔄 Syncing Canvas data...")
    # Ensure DB exists
    await init_db()
    courses = get_courses()
    await upsert_courses(courses)

    for course in courses:
        course_id = course["id"]
        assignments = get_assignments(course_id)
        await upsert_assignments(assignments, course_id)

    print("✅ Canvas data synced successfully.")