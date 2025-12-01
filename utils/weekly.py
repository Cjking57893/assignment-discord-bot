"""
Weekly assignment management utilities.
"""

import discord
import re
from datetime import datetime, timedelta
from typing import Tuple

from database.db_manager import (
    get_assignments_for_week,
    get_assignments_for_week_with_ids,
    upsert_study_plan
)
from utils.datetime_utils import format_local, get_local_tz, to_utc_iso_z
from constants import DAY_NAME_MAP, SCHEDULING_TIMEOUT


def _parse_day_time_input(input_str: str, week_monday: datetime) -> Tuple[datetime, None] | Tuple[None, str]:
    """
    Parse user input like 'Wed 7:30 PM' into a local datetime.
    
    Args:
        input_str: User input string (e.g., 'Wed 7:30 PM').
        week_monday: The Monday of the current week.
    
    Returns:
        Tuple of (parsed datetime, None) if successful, or (None, error message) if parsing fails.
    """
    match = re.match(r"^\s*([A-Za-z]+)\s+(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*$", input_str)
    if not match:
        return None, "Sorry, I didn't understand. Please use format like 'Wed 7:30 PM'."
    
    day_str, hh, mm, ap = match.groups()
    day_idx = DAY_NAME_MAP.get(day_str.lower())
    
    if day_idx is None:
        return None, "Unknown day. Try Mon/Tue/Wed/Thu/Fri/Sat/Sun."
    
    hour = int(hh) % 12
    if ap.lower() == 'pm':
        hour += 12
    minute = int(mm)
    
    planned_local = week_monday + timedelta(days=day_idx)
    planned_local = planned_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    planned_local = planned_local.replace(tzinfo=get_local_tz())
    
    return planned_local, None


async def send_weekly_assignments_to_channel(channel: discord.TextChannel) -> None:
    """
    Sends weekly assignments to a specific Discord channel without interactive scheduling.
    Used for automated Monday morning notifications.
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
        await channel.send(f"🎉 No assignments due for **{week_range}** — you're all caught up!")
        return

    # Build a neat message
    lines = []
    for name, due_at, course_name, course_code in assignments:
        # Convert due date to readable format
        try:
            due = format_local(due_at, "%a %b %d, %I:%M %p")
        except (ValueError, TypeError):
            due = due_at  # fallback if format is invalid

        course_label = f"{course_code}: {course_name}" if course_code else course_name
        lines.append(f"📚 **{name}** — *{course_label}*\n🕓 Due: `{due}`")

    message = f"📆 **Assignments due this week ({week_range}):**\n\n" + "\n\n".join(lines)
    message += "\n\n💡 Use `!thisweek` to schedule work times for these assignments!"

    await channel.send(message)


async def send_weekly_assignments(ctx: discord.ext.commands.Context) -> None:
    """List assignments due this week with interactive scheduling."""
    # Determine current week's Monday (00:00:00)
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    # Query the DB for assignments due this week
    assignments = await get_assignments_for_week(monday)

    # Format date range (for message header)
    tz = get_local_tz()
    tz_name = tz.tzname(None) if hasattr(tz, 'tzname') else ''
    week_range = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')} ({tz_name})"

    # Format the output
    if not assignments:
        await ctx.send(f"🎉 No assignments due for **{week_range}** — you're all caught up!")
        return

    # Build a neat message
    lines = []
    for name, due_at, course_name, course_code in assignments:
        try:
            due = format_local(due_at, "%a %b %d, %I:%M %p")
        except (ValueError, TypeError):
            due = due_at  # fallback if format is invalid

        course_label = f"{course_code}: {course_name}" if course_code else course_name
        lines.append(f"📚 **{name}** — *{course_label}*\n🕓 Due: `{due}`")

    message = f"📆 **Assignments due this week ({week_range}):**\n\n" + "\n\n".join(lines)

    await ctx.send(message)

    # Interactive scheduling
    await ctx.send("Let's schedule time to work on each assignment now. Please reply with a day/time like 'Wed 7:30 PM'. Type 'stop' to cancel the scheduling process.")

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # Fetch assignments with IDs for scheduling
    rows = await get_assignments_for_week_with_ids(monday)

    for aid, cid, aname, due_at, cname, ccode in rows:
        due_friendly = format_local(due_at, "%a %b %d, %I:%M %p") if due_at else "No due date"
        label = f"{ccode}: {cname}" if ccode else cname
        await ctx.send(f"Plan time for: {aname} — {label} (due {due_friendly})\nFormat: Mon/Tue/... HH:MM AM/PM. Type 'stop' to cancel.")

        while True:
            try:
                m = await ctx.bot.wait_for('message', timeout=SCHEDULING_TIMEOUT, check=check_author)
            except TimeoutError:
                # Timeout: keep prompting until provided
                await ctx.send("I didn't get a response. Please provide a day/time (e.g., 'Wed 7:30 PM') or type 'stop'.")
                continue
            
            content = m.content.strip()
            if content.lower() in ("stop", "quit"):
                await ctx.send("Scheduling cancelled. You can run !thisweek again to reschedule.")
                return

            # Parse time input
            planned_local, error = _parse_day_time_input(content, monday)
            if error:
                await ctx.send(error)
                continue
            
            # Save to database
            planned_utc_iso = to_utc_iso_z(planned_local)
            await upsert_study_plan(str(ctx.author.id), cid, aid, planned_utc_iso)
            await ctx.send(f"Saved plan for {aname} on {planned_local.strftime('%a %b %d at %I:%M %p')}.")
            break

