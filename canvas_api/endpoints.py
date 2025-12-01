"""Canvas API endpoint functions."""

from .client import CanvasClient
from typing import List, Dict, Any

canvas_client = CanvasClient()


def get_courses() -> List[Dict[str, Any]]:
    """Fetch all courses from Canvas for the current user."""
    data = canvas_client.get("courses")

    valid_courses: List[Dict[str, Any]] = []
    for course in data:
        # Skip malformed entries with no name
        if "name" not in course:
            continue

        valid_courses.append({
            "id": course["id"],
            "name": course.get("name"),
            "course_code": course.get("course_code"),
            "start_at": course.get("start_at"),
            "end_at": course.get("end_at")
        })

    return valid_courses


def get_assignments(course_id: int) -> List[Dict[str, Any]]:
    """Fetch all assignments for a given Canvas course."""
    data = canvas_client.get(f"courses/{course_id}/assignments")

    valid_assignments: List[Dict[str, Any]] = []
    for assignment in data:
        if "id" not in assignment or "name" not in assignment:
            continue

        valid_assignments.append({
            "id": assignment["id"],
            "name": assignment["name"],
            "due_at": assignment.get("due_at"),
            "html_url": assignment.get("html_url"),
            "has_submitted_submissions": assignment.get("has_submitted_submissions", False)
        })

    return valid_assignments


