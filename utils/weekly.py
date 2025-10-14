import discord
from datetime import datetime, timedelta
from database.db_manager import get_assignments_for_week
from utils.datetime_utils import format_local, get_local_tz

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
