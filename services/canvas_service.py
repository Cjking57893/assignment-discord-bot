from typing import List
from canvas_api.endpoints import get_courses, get_assignments
from utils.datetime_utils import format_local

def get_formatted_courses() -> List[str]:
    """
    Fetches courses from Canvas and returns a list of formatted strings.
    Example output: ['12345 – CS101: Intro to Programming']
    """
    courses = get_courses()
    formatted = []
    for c in courses:
        course_id = c.get("id", "N/A")
        name = c.get("name", "Unnamed Course")
        code = c.get("course_code", "")
        formatted.append(f"{course_id} – {code}: {name}" if code else f"{course_id} – {name}")
    return formatted


def get_formatted_assignments(course_id: int) -> List[str]:
    """
    Fetches assignments for a course and returns a list of formatted strings.
    Example output:
      ['📚 Project 1: API Design (due Oct 30, 2025, 11:59 PM) – 100 pts']
    """
    assignments = get_assignments(course_id)
    if not assignments:
        return ["No assignments found."]

    formatted = []
    for a in assignments:
        name = a.get("name", "Untitled Assignment")
        due_at = a.get("due_at")
        points = a.get("points_possible", 0)
        url = a.get("html_url", "")

        # Format due date nicely (Canvas returns ISO8601)
        if due_at:
            try:
                due_str = format_local(due_at)
            except Exception:
                due_str = due_at
        else:
            due_str = "No due date"

        formatted.append(f"📚 [{name}]({url}) – due {due_str} – {points} pts")

    return formatted
