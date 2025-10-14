import aiosqlite
from datetime import datetime, timedelta, timezone
from utils.datetime_utils import parse_canvas_datetime, to_utc_iso_z

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

        # Assignments table - use composite PK (course_id, id) to avoid cross-course ID collisions
        await db.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER,
                course_id INTEGER,
                name TEXT NOT NULL,
                due_at TEXT,
                week_number INTEGER,
                html_url TEXT,
                submitted INTEGER DEFAULT 0,
                PRIMARY KEY (course_id, id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        """)

        # Migration: if an older schema exists with single-column PK on id, rebuild table
        try:
            async with db.execute("PRAGMA table_info(assignments)") as cursor:
                cols = await cursor.fetchall()
                # cols: (cid, name, type, notnull, dflt_value, pk)
                pk_cols = [c[1] for c in cols if c[5] > 0]
            if pk_cols == ["id"]:
                # Rebuild table with composite PK
                await db.execute("BEGIN IMMEDIATE")
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assignments_new (
                        id INTEGER,
                        course_id INTEGER,
                        name TEXT NOT NULL,
                        due_at TEXT,
                        week_number INTEGER,
                        html_url TEXT,
                        submitted INTEGER DEFAULT 0,
                        PRIMARY KEY (course_id, id),
                        FOREIGN KEY (course_id) REFERENCES courses (id)
                    )
                    """
                )
                await db.execute(
                    """
                    INSERT OR REPLACE INTO assignments_new
                        (id, course_id, name, due_at, week_number, html_url, submitted)
                    SELECT id, course_id, name, due_at, week_number, html_url, submitted
                    FROM assignments
                    """
                )
                await db.execute("DROP TABLE assignments")
                await db.execute("ALTER TABLE assignments_new RENAME TO assignments")
                await db.execute("COMMIT")
        except Exception:
            # If anything goes wrong, try to rollback to avoid locking the DB
            try:
                await db.execute("ROLLBACK")
            except Exception:
                pass

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
            due_at_raw = a.get("due_at")
            week_num = None
            due_at_store = None
            if due_at_raw:
                dt = parse_canvas_datetime(due_at_raw)  # aware
                week_num = dt.isocalendar().week
                due_at_store = to_utc_iso_z(dt)

            await db.execute("""
                INSERT INTO assignments (id, course_id, name, due_at, week_number, html_url, submitted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id, id) DO UPDATE SET
                    name=excluded.name,
                    due_at=excluded.due_at,
                    week_number=excluded.week_number,
                    html_url=excluded.html_url,
                    submitted=excluded.submitted
            """, (
                a["id"],
                course_id,
                a["name"],
                due_at_store,
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
    # Treat provided start_date as local midnight Monday and compute end of week
    if start_date.tzinfo is None:
        # Assume local timezone for naive start_date; convert to UTC ranges
        local = datetime.now().astimezone().tzinfo or timezone.utc
        start_date = start_date.replace(tzinfo=local)
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)

    start_utc_iso = to_utc_iso_z(start_date)
    end_utc_iso = to_utc_iso_z(end_date)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT a.name, a.due_at, c.name AS course_name, c.course_code
            FROM assignments a
            JOIN courses c ON a.course_id = c.id
            WHERE a.due_at BETWEEN ? AND ?
            ORDER BY a.due_at
            """,
            (start_utc_iso, end_utc_iso),
        ) as cursor:
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
