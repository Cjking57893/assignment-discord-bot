import discord
from datetime import datetime, timedelta
from database.db_manager import get_assignments_for_week

async def send_weekly_assignments(ctx: discord.ext.commands.Context):
    """
    Sends a message listing all assignments due between Monday and Sunday of the current week.
    Assumes assignments have already been synced into the local SQLite database.
    """

    # 1. Determine current week's Monday (00:00:00)
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    # 2. Query the DB for assignments due this week
    assignments = await get_assignments_for_week(monday)

    # 3. Format date range (for message header)
    week_range = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')}"

    # 4. Format the output
    if not assignments:
        await ctx.send(f"🎉 No assignments due for **{week_range}** — you’re all caught up!")
        return

    # Build a neat message
    lines = []
    for name, due_at, course_name in assignments:
        # Convert due date to readable format
        try:
            due = datetime.fromisoformat(due_at.replace("Z", "+00:00")).strftime("%a %b %d, %I:%M %p")
        except Exception:
            due = due_at  # fallback if format is weird

        lines.append(f"📚 **{name}** — *{course_name}*\n🕓 Due: `{due}`")

    message = f"📆 **Assignments due this week ({week_range}):**\n\n" + "\n\n".join(lines)

    await ctx.send(message)
