from canvas_api.endpoints import get_courses, get_assignments

def main():
    courses = get_courses()
    with open("canvas_assignments_dump.txt", "w", encoding="utf-8") as f:
        for course in courses:
            course_id = course["id"]
            course_name = course.get("name", "")
            f.write(f"=== Course {course_id}: {course_name} ===\n")
            assignments = get_assignments(course_id)
            for a in assignments:
                name = a.get("name")
                due_at = a.get("due_at")
                f.write(f"  - {name} | due_at: {due_at}\n")
            f.write("\n")

if __name__ == "__main__":
    main()
