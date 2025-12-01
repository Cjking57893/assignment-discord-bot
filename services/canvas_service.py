"""Canvas service layer for formatting Canvas data."""

from typing import List
from canvas_api.endpoints import get_courses, get_assignments
from utils.datetime_utils import format_local


def get_formatted_courses() -> List[str]:
    """Fetch courses from Canvas and return formatted display strings."""
    courses = get_courses()
    formatted: List[str] = []
    
    for course in courses:
        course_id = course.get("id", "N/A")
        name = course.get("name", "Unnamed Course")
        code = course.get("course_code", "")
        
        if code:
            formatted.append(f"{course_id} – {code}: {name}")
        else:
            formatted.append(f"{course_id} – {name}")
    
    return formatted


def get_formatted_assignments(course_id: int) -> List[str]:
    """Fetch assignments for a course and return formatted display strings."""
    assignments = get_assignments(course_id)
    
    if not assignments:
        return ["No assignments found."]

    formatted: List[str] = []
    
    for assignment in assignments:
        name = assignment.get("name", "Untitled Assignment")
        due_at = assignment.get("due_at")
        points = assignment.get("points_possible", 0)
        url = assignment.get("html_url", "")

        # Format due date using datetime utility
        if due_at:
            try:
                due_str = format_local(due_at)
            except Exception:
                due_str = due_at
        else:
            due_str = "No due date"

        formatted.append(f"📚 [{name}]({url}) – due {due_str} – {points} pts")

    return formatted

