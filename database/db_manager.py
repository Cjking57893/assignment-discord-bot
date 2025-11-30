import aiosqlite
import os
from datetime import datetime, timedelta, timezone
from utils.datetime_utils import parse_canvas_datetime, to_utc_iso_z

DB_PATH = "data/canvas_bot.db"

# -------------------------------------------------------
# Initialization
# -------------------------------------------------------

async def init_db():
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
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

        # Study plans table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                user_id TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                assignment_id INTEGER NOT NULL,
                planned_at_utc TEXT NOT NULL,
                notes TEXT,
                PRIMARY KEY (user_id, course_id, assignment_id)
            )
        """)
        await db.commit()

        # Per-user assignment completion status
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_assignment_status (
                user_id TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                assignment_id INTEGER NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                completed_at_utc TEXT,
                PRIMARY KEY (user_id, course_id, assignment_id)
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


async def upsert_study_plan(user_id: str, course_id: int, assignment_id: int, planned_at_iso_utc: str, notes: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO study_plans (user_id, course_id, assignment_id, planned_at_utc, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, course_id, assignment_id) DO UPDATE SET
                planned_at_utc=excluded.planned_at_utc,
                notes=excluded.notes
            """,
            (user_id, course_id, assignment_id, planned_at_iso_utc, notes),
        )
        await db.commit()

async def get_study_plans_for_week(user_id: str, start_date_local: datetime):
    # Convert provided local range to UTC strings for querying
    if start_date_local.tzinfo is None:
        local = datetime.now().astimezone().tzinfo or timezone.utc
        start_date_local = start_date_local.replace(tzinfo=local)
    end_date_local = start_date_local + timedelta(days=6, hours=23, minutes=59, seconds=59)

    from utils.datetime_utils import to_utc_iso_z
    start_utc_iso = to_utc_iso_z(start_date_local)
    end_utc_iso = to_utc_iso_z(end_date_local)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT user_id, course_id, assignment_id, planned_at_utc, notes
            FROM study_plans
            WHERE planned_at_utc BETWEEN ? AND ? AND user_id = ?
            ORDER BY planned_at_utc
            """,
            (start_utc_iso, end_utc_iso, user_id),
        ) as cursor:
            return await cursor.fetchall()


async def get_user_plans_for_week_detailed(user_id: str, start_date_local: datetime):
    """
    Returns planned study sessions for the specified user for the week starting at
    start_date_local (treated as local Monday at 00:00), joined with assignment and
    course details for easier display.
    """
    # Normalize to local tz if naive
    if start_date_local.tzinfo is None:
        local = datetime.now().astimezone().tzinfo or timezone.utc
        start_date_local = start_date_local.replace(tzinfo=local)
    end_date_local = start_date_local + timedelta(days=6, hours=23, minutes=59, seconds=59)

    start_utc_iso = to_utc_iso_z(start_date_local)
    end_utc_iso = to_utc_iso_z(end_date_local)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT
                sp.assignment_id,
                sp.course_id,
                sp.planned_at_utc,
                sp.notes,
                a.name AS assignment_name,
                a.due_at AS assignment_due_utc,
                c.course_code,
                c.name AS course_name
            FROM study_plans sp
            JOIN assignments a ON a.id = sp.assignment_id AND a.course_id = sp.course_id
            JOIN courses c ON c.id = sp.course_id
            WHERE sp.user_id = ?
              AND sp.planned_at_utc BETWEEN ? AND ?
            ORDER BY sp.planned_at_utc
            """,
            (user_id, start_utc_iso, end_utc_iso),
        ) as cursor:
            return await cursor.fetchall()


async def set_assignment_completed(user_id: str, course_id: int, assignment_id: int, completed: bool, completed_at_iso_utc: str | None = None):
    """Mark an assignment as completed (or not) for a specific user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_assignment_status (user_id, course_id, assignment_id, completed, completed_at_utc)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, course_id, assignment_id) DO UPDATE SET
                completed=excluded.completed,
                completed_at_utc=excluded.completed_at_utc
            """,
            (user_id, course_id, assignment_id, int(completed), completed_at_iso_utc),
        )
        await db.commit()


async def get_week_assignments_with_status(user_id: str, start_date_local: datetime):
    """
    Get assignments due this week (Mon–Sun) with per-user completion status joined in.
    Returns rows of (assignment_id, course_id, assignment_name, due_at_utc, course_code, course_name, completed, submitted)
    """
    if start_date_local.tzinfo is None:
        local = datetime.now().astimezone().tzinfo or timezone.utc
        start_date_local = start_date_local.replace(tzinfo=local)
    end_date_local = start_date_local + timedelta(days=6, hours=23, minutes=59, seconds=59)

    start_utc_iso = to_utc_iso_z(start_date_local)
    end_utc_iso = to_utc_iso_z(end_date_local)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT a.id AS assignment_id,
                   a.course_id,
                   a.name AS assignment_name,
                   a.due_at AS due_at_utc,
                   c.course_code,
                   c.name AS course_name,
                   COALESCE(uas.completed, 0) AS completed,
                   COALESCE(a.submitted, 0) AS submitted
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            LEFT JOIN user_assignment_status uas
              ON uas.user_id = ? AND uas.course_id = a.course_id AND uas.assignment_id = a.id
            WHERE a.due_at BETWEEN ? AND ?
            ORDER BY a.due_at
            """,
            (user_id, start_utc_iso, end_utc_iso),
        ) as cursor:
            return await cursor.fetchall()
