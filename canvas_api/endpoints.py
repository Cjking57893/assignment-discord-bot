from .client import CanvasClient

canvas_client = CanvasClient()

def get_courses():
    return canvas_client.get("courses")

def get_assignments(course_id):
    return canvas_client.get(f"courses/{course_id}/assignments")