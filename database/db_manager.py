"""
Database Manager for Canvas Assignment Bot
Handles all SQLite database operations including:
- Schema initialization and migrations
- Course and assignment CRUD operations
- Study plans and user completion tracking
- Reminder state management
"""

import aiosqlite
import os
from datetime import datetime, timedelta, timezone
from utils.datetime_utils import parse_canvas_datetime, to_utc_iso_z

DB_PATH = "data/canvas_bot.db"


# ========================================
# Database Initialization
# ========================================

async def init_db():
    """Initialize database schema and perform any necessary migrations."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Create courses table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                course_code TEXT,
                start_at TEXT,
                end_at TEXT
            )
        """)

        # Create assignments table with composite PK to avoid cross-course ID collisions
        await db.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER,
                course_id INTEGER,
                name TEXT NOT NULL,
                due_at TEXT,
                week_number INTEGER,
                html_url TEXT,
                submitted INTEGER DEFAULT 0,
                due_reminder_2d_sent INTEGER DEFAULT 0,
                due_reminder_1d_sent INTEGER DEFAULT 0,
                due_reminder_12h_sent INTEGER DEFAULT 0,
                PRIMARY KEY (course_id, id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        """)
        
        # Migration: Add due date reminder columns if they don't exist
        for column in ["due_reminder_2d_sent", "due_reminder_1d_sent", "due_reminder_12h_sent"]:
            try:
                await db.execute(f"ALTER TABLE assignments ADD COLUMN {column} INTEGER DEFAULT 0")
            except Exception:
                pass

        # Migration: Rebuild assignments table if using old single-column PK schema
        try:
            async with db.execute("PRAGMA table_info(assignments)") as cursor:
                cols = await cursor.fetchall()
                pk_cols = [c[1] for c in cols if c[5] > 0]  # c[5] is pk flag
            
            if pk_cols == ["id"]:
                await db.execute("BEGIN IMMEDIATE")
                await db.execute("""
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
                """)
                await db.execute("""
                    INSERT OR REPLACE INTO assignments_new
                        (id, course_id, name, due_at, week_number, html_url, submitted)
                    SELECT id, course_id, name, due_at, week_number, html_url, submitted
                    FROM assignments
                """)
                await db.execute("DROP TABLE assignments")
                await db.execute("ALTER TABLE assignments_new RENAME TO assignments")
                await db.execute("COMMIT")
        except Exception:
            try:
                await db.execute("ROLLBACK")
            except Exception:
                pass

        await db.commit()

        # Create study plans table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                user_id TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                assignment_id INTEGER NOT NULL,
                planned_at_utc TEXT NOT NULL,
                notes TEXT,
                reminder_24h_sent INTEGER DEFAULT 0,
                reminder_1h_sent INTEGER DEFAULT 0,
                reminder_now_sent INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, course_id, assignment_id)
            )
        """)
        
        # Migration: Add reminder columns if they don't exist
        for column in ["reminder_24h_sent", "reminder_1h_sent", "reminder_now_sent"]:
            try:
                await db.execute(f"ALTER TABLE study_plans ADD COLUMN {column} INTEGER DEFAULT 0")
            except Exception:
                pass
        
        await db.commit()

        # Create user assignment completion tracking table
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

        # Create week completion notification tracking table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS week_completion_notifications (
                user_id TEXT NOT NULL,
                week_key TEXT NOT NULL,
                notified INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, week_key)
            )
        """)
        await db.commit()


# ========================================
# Course Operations
# ========================================

async def upsert_courses(courses: list[dict]):
    """Insert or update courses from Canvas API."""
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
    """Retrieve all courses from the database."""
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
    Get all assignments due during the specified week (Monday - Sunday).
    Returns: List of (name, due_at, course_name, course_code) tuples
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


async def get_assignments_for_week_with_ids(start_date: datetime):
    """
    Get all assignments due during the specified week with assignment and course IDs.
    Returns: List of (assignment_id, course_id, name, due_at, course_name, course_code) tuples
    """
    if start_date.tzinfo is None:
        local = datetime.now().astimezone().tzinfo or timezone.utc
        start_date = start_date.replace(tzinfo=local)
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)

    start_utc_iso = to_utc_iso_z(start_date)
    end_utc_iso = to_utc_iso_z(end_date)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT a.id, a.course_id, a.name, a.due_at, c.name AS course_name, c.course_code
            FROM assignments a
            JOIN courses c ON a.course_id = c.id
            WHERE a.due_at BETWEEN ? AND ?
            ORDER BY a.due_at
            """,
            (start_utc_iso, end_utc_iso),
        ) as cursor:
            return await cursor.fetchall()

async def get_all_assignments() -> list[tuple]:
    """Retrieve all assignments from the database."""
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


# ========================================
# Assignment Completion Tracking
# ========================================

async def set_assignment_completed(user_id: str, course_id: int, assignment_id: int, completed: bool, completed_at_iso_utc: str | None = None):
    """Mark an assignment as completed or incomplete for a specific user."""
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
    Get assignments due this week with per-user completion status.
    Returns: List of (assignment_id, course_id, name, due_at, course_code, course_name, completed, submitted) tuples
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


# ========================================
# Work Session Reminder Operations
# ========================================

async def get_pending_reminders(now_utc: datetime):
    """
    Get all planned sessions that need reminders sent (24h, 1h, or now).
    Returns: List of tuples with session details and reminder type
    """
    now_utc_iso = to_utc_iso_z(now_utc)
    h24_later = now_utc + timedelta(hours=24)
    h24_later_iso = to_utc_iso_z(h24_later)
    h1_later = now_utc + timedelta(hours=1)
    h1_later_iso = to_utc_iso_z(h1_later)
    
    results = []
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Check for 24-hour reminders (planned time is 24 hours from now, +/- 1 minute)
        h24_start = to_utc_iso_z(now_utc + timedelta(hours=24, minutes=-1))
        h24_end = to_utc_iso_z(now_utc + timedelta(hours=24, minutes=1))
        async with db.execute(
            """
            SELECT sp.user_id, sp.course_id, sp.assignment_id, sp.planned_at_utc,
                   a.name, a.due_at, c.course_code, c.name
            FROM study_plans sp
            JOIN assignments a ON a.id = sp.assignment_id AND a.course_id = sp.course_id
            JOIN courses c ON c.id = sp.course_id
            WHERE sp.planned_at_utc BETWEEN ? AND ?
              AND sp.reminder_24h_sent = 0
            """,
            (h24_start, h24_end),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(row + ('24h',))
        
        # Check for 1-hour reminders
        h1_start = to_utc_iso_z(now_utc + timedelta(hours=1, minutes=-1))
        h1_end = to_utc_iso_z(now_utc + timedelta(hours=1, minutes=1))
        async with db.execute(
            """
            SELECT sp.user_id, sp.course_id, sp.assignment_id, sp.planned_at_utc,
                   a.name, a.due_at, c.course_code, c.name
            FROM study_plans sp
            JOIN assignments a ON a.id = sp.assignment_id AND a.course_id = sp.course_id
            JOIN courses c ON c.id = sp.course_id
            WHERE sp.planned_at_utc BETWEEN ? AND ?
              AND sp.reminder_1h_sent = 0
            """,
            (h1_start, h1_end),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(row + ('1h',))
        
        # Check for "now" reminders (within 1 minute of planned time)
        now_start = to_utc_iso_z(now_utc + timedelta(minutes=-1))
        now_end = to_utc_iso_z(now_utc + timedelta(minutes=1))
        async with db.execute(
            """
            SELECT sp.user_id, sp.course_id, sp.assignment_id, sp.planned_at_utc,
                   a.name, a.due_at, c.course_code, c.name
            FROM study_plans sp
            JOIN assignments a ON a.id = sp.assignment_id AND a.course_id = sp.course_id
            JOIN courses c ON c.id = sp.course_id
            WHERE sp.planned_at_utc BETWEEN ? AND ?
              AND sp.reminder_now_sent = 0
            """,
            (now_start, now_end),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(row + ('now',))
    
    return results


async def mark_reminder_sent(user_id: str, course_id: int, assignment_id: int, reminder_type: str):
    """Mark a specific reminder as sent for a study plan."""
    column_map = {
        '24h': 'reminder_24h_sent',
        '1h': 'reminder_1h_sent',
        'now': 'reminder_now_sent'
    }
    column = column_map.get(reminder_type)
    if not column:
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"""
            UPDATE study_plans
            SET {column} = 1
            WHERE user_id = ? AND course_id = ? AND assignment_id = ?
            """,
            (user_id, course_id, assignment_id),
        )
        await db.commit()


async def update_study_plan_time(user_id: str, course_id: int, assignment_id: int, new_planned_at_utc: str):
    """Update the planned time for a study session and reset all reminder flags."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE study_plans
            SET planned_at_utc = ?,
                reminder_24h_sent = 0,
                reminder_1h_sent = 0,
                reminder_now_sent = 0
            WHERE user_id = ? AND course_id = ? AND assignment_id = ?
            """,
            (new_planned_at_utc, user_id, course_id, assignment_id),
        )
        await db.commit()


# ========================================
# Due Date Reminder Operations
# ========================================

async def get_pending_due_date_reminders(now_utc: datetime, user_id: str):
    """
    Get assignments that need due date reminders sent (2d, 1d, or 12h before due).
    Only includes incomplete assignments for the current week.
    Returns: List of tuples with assignment details and reminder type
    """
    # Get current week Monday-Sunday
    today = now_utc.astimezone(get_local_tz() if hasattr(now_utc, 'astimezone') else None)
    if today.tzinfo is None:
        from datetime import timezone as tz
        today = now_utc.replace(tzinfo=tz.utc).astimezone(get_local_tz())
    
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    start_utc_iso = to_utc_iso_z(monday)
    end_utc_iso = to_utc_iso_z(sunday)
    
    results = []
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Check for 2-day reminders (due date is 2 days from now, +/- 1 minute)
        d2_start = to_utc_iso_z(now_utc + timedelta(days=2, minutes=-1))
        d2_end = to_utc_iso_z(now_utc + timedelta(days=2, minutes=1))
        async with db.execute(
            """
            SELECT a.id, a.course_id, a.name, a.due_at, c.course_code, c.name
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            LEFT JOIN user_assignment_status uas 
              ON uas.user_id = ? AND uas.course_id = a.course_id AND uas.assignment_id = a.id
            WHERE a.due_at BETWEEN ? AND ?
              AND a.due_at BETWEEN ? AND ?
              AND a.due_reminder_2d_sent = 0
              AND COALESCE(uas.completed, 0) = 0
            """,
            (user_id, d2_start, d2_end, start_utc_iso, end_utc_iso),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(row + ('2d',))
        
        # Check for 1-day reminders
        d1_start = to_utc_iso_z(now_utc + timedelta(days=1, minutes=-1))
        d1_end = to_utc_iso_z(now_utc + timedelta(days=1, minutes=1))
        async with db.execute(
            """
            SELECT a.id, a.course_id, a.name, a.due_at, c.course_code, c.name
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            LEFT JOIN user_assignment_status uas 
              ON uas.user_id = ? AND uas.course_id = a.course_id AND uas.assignment_id = a.id
            WHERE a.due_at BETWEEN ? AND ?
              AND a.due_at BETWEEN ? AND ?
              AND a.due_reminder_1d_sent = 0
              AND COALESCE(uas.completed, 0) = 0
            """,
            (user_id, d1_start, d1_end, start_utc_iso, end_utc_iso),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(row + ('1d',))
        
        # Check for 12-hour reminders
        h12_start = to_utc_iso_z(now_utc + timedelta(hours=12, minutes=-1))
        h12_end = to_utc_iso_z(now_utc + timedelta(hours=12, minutes=1))
        async with db.execute(
            """
            SELECT a.id, a.course_id, a.name, a.due_at, c.course_code, c.name
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            LEFT JOIN user_assignment_status uas 
              ON uas.user_id = ? AND uas.course_id = a.course_id AND uas.assignment_id = a.id
            WHERE a.due_at BETWEEN ? AND ?
              AND a.due_at BETWEEN ? AND ?
              AND a.due_reminder_12h_sent = 0
              AND COALESCE(uas.completed, 0) = 0
            """,
            (user_id, h12_start, h12_end, start_utc_iso, end_utc_iso),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(row + ('12h',))
    
    return results


async def mark_due_date_reminder_sent(course_id: int, assignment_id: int, reminder_type: str):
    """Mark a specific due date reminder as sent for an assignment."""
    column_map = {
        '2d': 'due_reminder_2d_sent',
        '1d': 'due_reminder_1d_sent',
        '12h': 'due_reminder_12h_sent'
    }
    column = column_map.get(reminder_type)
    if not column:
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"""
            UPDATE assignments
            SET {column} = 1
            WHERE course_id = ? AND id = ?
            """,
            (course_id, assignment_id),
        )
        await db.commit()


# ========================================
# Week Completion Tracking
# ========================================

async def check_week_completion(user_id: str, start_date_local: datetime):
    """
    Check if all assignments for the current week are completed.
    Returns: (all_complete: bool, total_count: int, completed_count: int)
    """
    if start_date_local.tzinfo is None:
        local = datetime.now().astimezone().tzinfo or timezone.utc
        start_date_local = start_date_local.replace(tzinfo=local)
    end_date_local = start_date_local + timedelta(days=6, hours=23, minutes=59, seconds=59)

    start_utc_iso = to_utc_iso_z(start_date_local)
    end_utc_iso = to_utc_iso_z(end_date_local)

    async with aiosqlite.connect(DB_PATH) as db:
        # Get total assignments for the week
        async with db.execute(
            """
            SELECT COUNT(*)
            FROM assignments a
            WHERE a.due_at BETWEEN ? AND ?
            """,
            (start_utc_iso, end_utc_iso),
        ) as cursor:
            row = await cursor.fetchone()
            total_count = row[0] if row else 0
        
        if total_count == 0:
            return (True, 0, 0)  # No assignments = all complete
        
        # Get completed assignments for this user
        async with db.execute(
            """
            SELECT COUNT(*)
            FROM assignments a
            JOIN user_assignment_status uas
              ON uas.user_id = ? AND uas.course_id = a.course_id AND uas.assignment_id = a.id
            WHERE a.due_at BETWEEN ? AND ?
              AND uas.completed = 1
            """,
            (user_id, start_utc_iso, end_utc_iso),
        ) as cursor:
            row = await cursor.fetchone()
            completed_count = row[0] if row else 0
        
        all_complete = (completed_count == total_count)
        return (all_complete, total_count, completed_count)


async def get_week_completion_notified(user_id: str, week_start: datetime):
    """Check if completion notification was already sent for this week."""
    week_key = week_start.strftime("%Y-%U")  # Year-Week format
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT notified
            FROM week_completion_notifications
            WHERE user_id = ? AND week_key = ?
            """,
            (user_id, week_key),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def mark_week_completion_notified(user_id: str, week_start: datetime):
    """Mark that completion notification was sent for this week."""
    week_key = week_start.strftime("%Y-%U")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO week_completion_notifications (user_id, week_key, notified)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, week_key) DO UPDATE SET notified=1
            """,
            (user_id, week_key),
        )
        await db.commit()
