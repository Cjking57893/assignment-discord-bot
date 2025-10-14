import discord
from datetime import datetime, timedelta
from database.db_manager import get_assignments_for_week, upsert_study_plan
from utils.datetime_utils import format_local, get_local_tz, parse_canvas_datetime, to_utc_iso_z

async def send_weekly_assignments(ctx: discord.ext.commands.Context):
    """
    Sends a message listing all assignments due between Monday and Sunday of the current week.
    Assumes assignments have already been synced into the local SQLite database.
    """

    # 1. Determine current week's Monday (00:00:00)
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    # 2. Query the DB for assignments due this week
    assignments = await get_assignments_for_week(monday)

    # 3. Format date range (for message header)
    tz = get_local_tz()
    week_range = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')} ({tz.tzname(None) if hasattr(tz, 'tzname') else ''})"

    # 4. Format the output
    if not assignments:
        await ctx.send(f"🎉 No assignments due for **{week_range}** — you’re all caught up!")
        return

    # Build a neat message
    lines = []
    for name, due_at, course_name, course_code in assignments:
        # Convert due date to readable format
        try:
            due = format_local(due_at, "%a %b %d, %I:%M %p")
        except Exception:
            due = due_at  # fallback if format is weird

        course_label = f"{course_code}: {course_name}" if course_code else course_name
        lines.append(f"📚 **{name}** — *{course_label}*\n🕓 Due: `{due}`")

    message = f"📆 **Assignments due this week ({week_range}):**\n\n" + "\n\n".join(lines)

    await ctx.send(message)

    # Interactive scheduling (required): the user must plan a time for each assignment
    await ctx.send("Let's schedule time to work on each assignment now. Please reply with a day/time like 'Wed 7:30 PM'. Type 'stop' to cancel the scheduling process.")

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # Re-fetch assignments to get IDs and course IDs for storage
    from aiosqlite import connect as _connect
    # We'll query the DB directly to map names/due to (assignment_id, course_id)
    # to keep it simple for now.
    import aiosqlite
    async with aiosqlite.connect("data/canvas_bot.db") as db:
        # Build a quick lookup for this week's assignments
        # Note: We already have 'assignments' tuples without IDs; fetch with IDs
        # between same UTC window
        start_local = monday
        if start_local.tzinfo is None:
            start_local = start_local.replace(tzinfo=get_local_tz())
        end_local = sunday.replace(hour=23, minute=59, second=59)
        if end_local.tzinfo is None:
            end_local = end_local.replace(tzinfo=get_local_tz())
        start_utc = to_utc_iso_z(start_local)
        end_utc = to_utc_iso_z(end_local)
        async with db.execute(
            """
            SELECT a.id, a.course_id, a.name, a.due_at, c.name as course_name, c.course_code
            FROM assignments a
            JOIN courses c ON a.course_id = c.id
            WHERE a.due_at BETWEEN ? AND ?
            ORDER BY a.due_at
            """,
            (start_utc, end_utc),
        ) as cur:
            rows = await cur.fetchall()

    for aid, cid, aname, due_at, cname, ccode in rows:
        due_friendly = format_local(due_at, "%a %b %d, %I:%M %p") if due_at else "No due date"
        label = f"{ccode}: {cname}" if ccode else cname
        await ctx.send(f"Plan time for: {aname} — {label} (due {due_friendly})\nFormat: Mon/Tue/... HH:MM AM/PM. Type 'stop' to cancel.")

        attempts = 0
        while True:
            attempts += 1
            try:
                m = await ctx.bot.wait_for('message', timeout=120.0, check=check_author)
            except Exception:
                # Timeout: keep prompting until provided (forced planning)
                await ctx.send("I didn't get a response. Please provide a day/time (e.g., 'Wed 7:30 PM') or type 'stop'.")
                continue
            content = m.content.strip()
            if content.lower() in ("stop", "quit"):
                await ctx.send("Scheduling cancelled. You can run !thisweek again to reschedule.")
                return

            # Parse simple inputs like 'Wed 7:30 PM' relative to current week
            day_map = {
                'mon': 0, 'monday': 0,
                'tue': 1, 'tues': 1, 'tuesday': 1,
                'wed': 2, 'wednesday': 2,
                'thu': 3, 'thurs': 3, 'thursday': 3,
                'fri': 4, 'friday': 4,
                'sat': 5, 'saturday': 5,
                'sun': 6, 'sunday': 6,
            }
            import re
            match = re.match(r"^\s*([A-Za-z]+)\s+(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*$", content)
            if not match:
                await ctx.send("Sorry, I didn't understand. Please use 'Wed 7:30 PM'.")
                continue
            day_str, hh, mm, ap = match.groups()
            day_idx = day_map.get(day_str.lower())
            if day_idx is None:
                await ctx.send("Unknown day. Try Mon/Tue/Wed/Thu/Fri/Sat/Sun.")
                continue
            hour = int(hh) % 12
            if ap.lower() == 'pm':
                hour += 12
            minute = int(mm)
            planned_local = monday + timedelta(days=day_idx)
            planned_local = planned_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            planned_local = planned_local.replace(tzinfo=get_local_tz())
            planned_utc_iso = to_utc_iso_z(planned_local)
            await upsert_study_plan(str(ctx.author.id), cid, aid, planned_utc_iso)
            await ctx.send(f"Saved plan for {aname} on {planned_local.strftime('%a %b %d at %I:%M %p')}.")
            break
