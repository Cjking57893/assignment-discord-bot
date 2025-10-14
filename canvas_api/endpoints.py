from .client import CanvasClient

canvas_client = CanvasClient()

def get_courses():
    """
    Fetch all courses from Canvas for the current user.
    Filters out restricted or missing course data.
    """
    data = canvas_client.get("courses", params={"enrollment_state": "active"})

    valid_courses = []
    for c in data:
        # Skip restricted / malformed entries
        if "name" not in c:
            print(f"⚠️ Skipping restricted course {c.get('id')}")
            continue

        valid_courses.append({
            "id": c["id"],
            "name": c.get("name"),
            "course_code": c.get("course_code"),
            "start_at": c.get("start_at"),
            "end_at": c.get("end_at")
        })

    return valid_courses


def get_assignments(course_id: int):
    """
    Fetch all assignments for a given Canvas course.
    Only includes assignments that have valid IDs and names.
    """
    data = canvas_client.get(f"courses/{course_id}/assignments")

    valid_assignments = []
    for a in data:
        if "id" not in a or "name" not in a:
            continue

        valid_assignments.append({
            "id": a["id"],
            "name": a["name"],
            "due_at": a.get("due_at"),
            "html_url": a.get("html_url"),
            "has_submitted_submissions": a.get("has_submitted_submissions", False)
        })

    return valid_assignments

