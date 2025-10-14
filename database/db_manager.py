import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "data/canvas_bot.db"

# -------------------------------------------------------
# Initialization
# -------------------------------------------------------

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Courses table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                course_code TEXT,
                start_at TEXT,
                end_at TEXT
            )
        """)

        # Assignments table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY,
                course_id INTEGER,
                name TEXT NOT NULL,
                due_at TEXT,
                week_number INTEGER,
                html_url TEXT,
                submitted INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        """)

        await db.commit()

# -------------------------------------------------------
# Course Functions
# -------------------------------------------------------

async def upsert_courses(courses: list[dict]):
    """Insert or update courses returned by Canvas API"""
    async with aiosqlite.connect(DB_PATH) as db:
        for c in courses:
            await db.execute("""
                INSERT INTO courses (id, name, course_code, start_at, end_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    course_code=excluded.course_code,
                    start_at=excluded.start_at,
                    end_at=excluded.end_at
            """, (c["id"], c["name"], c.get("course_code"), c.get("start_at"), c.get("end_at")))
        await db.commit()

async def get_courses() -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name, course_code FROM courses ORDER BY name") as cursor:
            return await cursor.fetchall()

# -------------------------------------------------------
# Assignment Functions
# -------------------------------------------------------

async def upsert_assignments(assignments: list[dict], course_id: int):
    """Insert or update assignments for a specific course"""
    async with aiosqlite.connect(DB_PATH) as db:
        for a in assignments:
            due_at = a.get("due_at")
            week_num = None
            if due_at:
                dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
                week_num = dt.isocalendar().week

            await db.execute("""
                INSERT INTO assignments (id, course_id, name, due_at, week_number, html_url, submitted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    due_at=excluded.due_at,
                    week_number=excluded.week_number,
                    html_url=excluded.html_url,
                    submitted=excluded.submitted
            """, (
                a["id"],
                course_id,
                a["name"],
                due_at,
                week_num,
                a.get("html_url"),
                int(a.get("has_submitted_submissions", False))
            ))
        await db.commit()

async def get_assignments_for_week(start_date: datetime):
    """
    Returns all assignments due between start_date (Monday) and Sunday of that week.
    :param start_date: datetime object representing Monday of the week.
    """
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT a.name, a.due_at, c.name AS course_name
            FROM assignments a
            JOIN courses c ON a.course_id = c.id
            WHERE datetime(a.due_at) BETWEEN datetime(?) AND datetime(?)
            ORDER BY a.due_at
        """, (start_date.isoformat(), end_date.isoformat())) as cursor:
            return await cursor.fetchall()

async def get_all_assignments() -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT a.name, a.due_at, c.name AS course_name
            FROM assignments a
            JOIN courses c ON a.course_id = c.id
            ORDER BY a.due_at
        """) as cursor:
            return await cursor.fetchall()
