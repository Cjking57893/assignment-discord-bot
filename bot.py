"""
Discord Bot for Canvas Assignment Management
Provides automated weekly notifications, reminders, and interactive planning for Canvas assignments.
"""

import re
import discord
from discord.ext import commands, tasks
from datetime import time, datetime, timedelta, timezone

from config import BOT_TOKEN, CHANNEL_ID, WEEKLY_NOTIFICATION_HOUR, WEEKLY_NOTIFICATION_MINUTE
from database.db_manager import (
    init_db, get_user_plans_for_week_detailed, get_week_assignments_with_status, 
    set_assignment_completed, get_pending_reminders, mark_reminder_sent, update_study_plan_time,
    get_pending_due_date_reminders, mark_due_date_reminder_sent, check_week_completion,
    get_week_completion_notified, mark_week_completion_notified
)
from utils.weekly import send_weekly_assignments, send_weekly_assignments_to_channel
from utils.sync import sync_canvas_data
from utils.datetime_utils import format_local, get_local_tz, to_utc_iso_z

# ========================================
# Bot Initialization
# ========================================

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
_synced_once = False

# ========================================
# Constants
# ========================================

WORK_SESSION_REMINDER_LABELS = {
    '24h': '⏰ **24-hour reminder**',
    '1h': '⏰ **1-hour reminder**',
    'now': '🔔 **It\'s time!**'
}

DUE_DATE_REMINDER_LABELS = {
    '2d': '📅 **2-day reminder**',
    '1d': '📅 **1-day reminder**',
    '12h': '⚠️ **12-hour reminder**'
}

DUE_DATE_REMINDER_MESSAGES = {
    '2d': "💡 You have 2 days to complete this assignment!",
    '1d': "⚡ Only 1 day left to complete this assignment!",
    '12h': "🚨 Only 12 hours left! Time to finish up!"
}


# ========================================
# Helper Functions
# ========================================

def parse_day_time_input(input_str: str, week_monday: datetime) -> str | None:
    """
    Parse user input like 'Wed 7:30 PM' into a UTC ISO timestamp.
    Returns None if parsing fails.
    """
    day_map = {
        'mon': 0, 'monday': 0,
        'tue': 1, 'tues': 1, 'tuesday': 1,
        'wed': 2, 'wednesday': 2,
        'thu': 3, 'thurs': 3, 'thursday': 3,
        'fri': 4, 'friday': 4,
        'sat': 5, 'saturday': 5,
        'sun': 6, 'sunday': 6,
    }
    
    match = re.match(r"^\s*([A-Za-z]+)\s+(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*$", input_str)
    if not match:
        return None
    
    day_str, hh, mm, ap = match.groups()
    day_idx = day_map.get(day_str.lower())
    if day_idx is None:
        return None
    
    hour = int(hh) % 12
    if ap.lower() == 'pm':
        hour += 12
    minute = int(mm)
    
    planned_local = week_monday + timedelta(days=day_idx)
    planned_local = planned_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    planned_local = planned_local.replace(tzinfo=get_local_tz())
    
    return to_utc_iso_z(planned_local)


# ========================================
# Event Handlers
# ========================================

@bot.event
async def on_ready():
    """Initialize bot, sync Canvas data, and start background tasks."""
    global _synced_once
    await init_db()
    print("Database initialized.")
    print(f"✅ Logged in as {bot.user}")
    
    # Perform initial Canvas sync
    if not _synced_once:
        try:
            await sync_canvas_data()
            _synced_once = True
            print("Initial sync complete.")
        except Exception as e:
            print(f"Initial sync failed: {e}")
    
    # Start background tasks
    if not weekly_notification.is_running():
        weekly_notification.start()
    
    if not check_reminders.is_running():
        check_reminders.start()
        print("⏰ Reminder system started.")


# ========================================
# User Commands
# ========================================

@bot.command()
async def sync(ctx):
    """Manually sync Canvas courses and assignments to local database."""
    await ctx.send("🔄 Syncing Canvas data from Canvas API...")
    try:
        await sync_canvas_data()
        await ctx.send("✅ Sync complete! Local database updated.")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")


@bot.command()
async def thisweek(ctx):
    """List assignments due this week and interactively schedule work sessions."""
    await send_weekly_assignments(ctx)


@bot.command()
async def plans(ctx):
    """Display all planned study sessions for the current week."""
    tz = get_local_tz()
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    user_id = str(ctx.author.id)
    rows = await get_user_plans_for_week_detailed(user_id, monday)

    tz_label = tz.tzname(None) if hasattr(tz, 'tzname') else ''
    header_range = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')} ({tz_label})"

    if not rows:
        await ctx.send(f"You have no planned sessions for {header_range}. Use !thisweek to add some.")
        return

    # Format each planned session
    lines = []
    for (assignment_id, course_id, planned_at_utc, notes, assignment_name, 
         assignment_due_utc, course_code, course_name) in rows:
        planned_local = format_local(planned_at_utc, "%a %b %d, %I:%M %p")
        due_str = format_local(assignment_due_utc, "%a %b %d, %I:%M %p") if assignment_due_utc else "No due date"
        course_label = f"{course_code}: {course_name}" if course_code else course_name
        note_str = f"\n📝 {notes}" if notes else ""
        lines.append(f"📚 {assignment_name} — {course_label}\n🕒 When: `{planned_local}`\n⏳ Due: `{due_str}`{note_str}")

    msg = f"🗓️ Your planned sessions for this week ({header_range}):\n\n" + "\n\n".join(lines)
    await ctx.send(msg)


@bot.command()
async def complete(ctx, *, query: str | None = None):
    """
    Mark assignments as complete.
    Usage: !complete [search_query]
    - With query: searches for assignments matching the query
    - Without query: shows numbered list of incomplete assignments for selection
    """
    tz = get_local_tz()
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())

    user_id = str(ctx.author.id)
    rows = await get_week_assignments_with_status(user_id, monday)

    # Filter to incomplete assignments only
    items = [r for r in rows if int(r[6]) == 0]

    # Apply search query if provided
    if query:
        q = query.lower()
        items = [r for r in items if q in (r[2] or '').lower()]
        if not items:
            await ctx.send("No matching incomplete assignments found for your query.")
            return

    if not items:
        await ctx.send("You have no incomplete assignments for this week. Nice!")
        return

    # Display numbered list
    def fmt_row(i, r):
        assignment_id, course_id, assignment_name, due_utc, course_code, course_name, completed, submitted = r
        due_str = format_local(due_utc, "%a %b %d, %I:%M %p") if due_utc else "No due date"
        label = f"{course_code}: {course_name}" if course_code else course_name
        submitted_tag = " • submitted" if int(submitted) else ""
        return f"{i}. {assignment_name} — {label} (due {due_str}{submitted_tag})"

    listing = "\n".join(fmt_row(i+1, r) for i, r in enumerate(items))
    await ctx.send("Select the assignments to mark complete (e.g., '1,3,5'):\n" + listing)

    # Wait for user response
    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        m = await ctx.bot.wait_for('message', timeout=90.0, check=check_author)
    except TimeoutError:
        await ctx.send("Timed out waiting for a selection.")
        return

    # Parse selection (supports comma-separated numbers)
    selection = m.content.strip()
    picks = []
    for part in re.split(r"\s*,\s*", selection):
        if not part.isdigit():
            continue
        idx = int(part) - 1
        if 0 <= idx < len(items):
            picks.append(idx)

    if not picks:
        await ctx.send("No valid selections. Cancelled.")
        return

    # Mark selected assignments as completed
    now_local = datetime.now().astimezone(tz)
    now_utc_iso = to_utc_iso_z(now_local)
    count = 0
    for idx in picks:
        assignment_id, course_id, *_ = items[idx]
        await set_assignment_completed(user_id, int(course_id), int(assignment_id), True, now_utc_iso)
        count += 1

    await ctx.send(f"Marked {count} assignment(s) as completed.")


@bot.command()
async def reschedule(ctx):
    """Interactively reschedule a planned work session to a new time."""
    tz = get_local_tz()
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    
    user_id = str(ctx.author.id)
    rows = await get_user_plans_for_week_detailed(user_id, monday)
    
    if not rows:
        await ctx.send("You have no planned sessions to reschedule. Use !thisweek to create some.")
        return
    
    # Display numbered list of planned sessions
    lines = []
    for i, (assignment_id, course_id, planned_at_utc, notes, assignment_name, 
           assignment_due_utc, course_code, course_name) in enumerate(rows, 1):
        planned_local = format_local(planned_at_utc, "%a %b %d, %I:%M %p")
        course_label = f"{course_code}: {course_name}" if course_code else course_name
        lines.append(f"{i}. {assignment_name} — {course_label} (scheduled {planned_local})")
    
    await ctx.send("Which session do you want to reschedule? Enter the number:\n" + "\n".join(lines))
    
    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    # Get session selection
    try:
        selection_msg = await ctx.bot.wait_for('message', timeout=60.0, check=check_author)
    except TimeoutError:
        await ctx.send("Timed out waiting for selection.")
        return
    
    if not selection_msg.content.isdigit():
        await ctx.send("Invalid selection. Cancelled.")
        return
    
    idx = int(selection_msg.content) - 1
    if idx < 0 or idx >= len(rows):
        await ctx.send("Invalid selection. Cancelled.")
        return
    
    assignment_id, course_id, old_planned_at, notes, assignment_name, assignment_due_utc, course_code, course_name = rows[idx]
    
    # Get new time
    await ctx.send(f"Enter the new time for **{assignment_name}** (e.g., 'Wed 7:30 PM'):")
    
    try:
        time_msg = await ctx.bot.wait_for('message', timeout=120.0, check=check_author)
    except TimeoutError:
        await ctx.send("Timed out waiting for new time.")
        return
    
    # Parse time input
    new_planned_utc_iso = parse_day_time_input(time_msg.content, monday)
    if not new_planned_utc_iso:
        await ctx.send("Sorry, I didn't understand. Please use format like 'Wed 7:30 PM'.")
        return
    
    # Update the database (resets all reminder flags)
    await update_study_plan_time(user_id, course_id, assignment_id, new_planned_utc_iso)
    
    new_time_str = format_local(new_planned_utc_iso, "%a %b %d at %I:%M %p")
    await ctx.send(f"✅ Rescheduled **{assignment_name}** to {new_time_str}. Reminders have been reset.")


# ========================================
# Background Tasks
# ========================================

@tasks.loop(time=time(hour=WEEKLY_NOTIFICATION_HOUR, minute=WEEKLY_NOTIFICATION_MINUTE))
async def weekly_notification():
    """Send weekly assignment summary every Monday at configured time."""
    # Only run on Mondays
    if datetime.now().weekday() != 0:
        return
    
    # Sync Canvas data before sending weekly update
    try:
        await sync_canvas_data()
        print("Weekly sync complete.")
    except Exception as e:
        print(f"Weekly sync failed: {e}")
    
    # Validate channel configuration
    if not CHANNEL_ID:
        print("⚠️ CHANNEL_ID not configured. Skipping weekly notification.")
        return
    
    try:
        channel_id = int(CHANNEL_ID)
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"⚠️ Could not find channel with ID {channel_id}")
            return
        
        await send_weekly_assignments_to_channel(channel)
        print("📅 Weekly Monday scheduling message sent!")
    except ValueError:
        print(f"⚠️ Invalid CHANNEL_ID: {CHANNEL_ID}")
    except Exception as e:
        print(f"❌ Error sending weekly notification: {e}")


@tasks.loop(minutes=1)
async def check_reminders():
    """Check and send work session and due date reminders every minute."""
    if not CHANNEL_ID:
        return
    
    try:
        channel_id = int(CHANNEL_ID)
        channel = bot.get_channel(channel_id)
        if not channel:
            return
        
        now_utc = datetime.now(timezone.utc)
        
        # ===== Work Session Reminders =====
        await send_work_session_reminders(channel, now_utc)
        
        # ===== Due Date Reminders =====
        await send_due_date_reminders(channel, now_utc)
        
        # ===== Week Completion Check (once daily at noon) =====
        if now_utc.hour == 12:
            await check_and_send_completion_notifications(channel)
            
    except Exception as e:
        print(f"❌ Error checking reminders: {e}")


# ========================================
# Reminder Helper Functions
# ========================================

async def send_work_session_reminders(channel: discord.TextChannel, now_utc: datetime):
    """Send reminders for upcoming planned work sessions."""
    reminders = await get_pending_reminders(now_utc)
    
    for reminder in reminders:
        user_id, course_id, assignment_id, planned_at_utc, assignment_name, due_at, course_code, course_name, reminder_type = reminder
        
        time_label = WORK_SESSION_REMINDER_LABELS.get(reminder_type, '⏰ Reminder')
        
        planned_local = format_local(planned_at_utc, "%a %b %d, %I:%M %p")
        due_str = format_local(due_at, "%a %b %d, %I:%M %p") if due_at else "No due date"
        course_label = f"{course_code}: {course_name}" if course_code else course_name
        
        msg = f"{time_label} <@{user_id}>\n\n"
        msg += f"📚 **Planned work session for:** {assignment_name}\n"
        msg += f"📖 **Course:** {course_label}\n"
        msg += f"🕒 **Scheduled time:** {planned_local}\n"
        msg += f"⏳ **Due:** {due_str}\n\n"
        msg += f"💡 Reply with `!reschedule` to change the time for this session."
        
        await channel.send(msg)
        await mark_reminder_sent(user_id, course_id, assignment_id, reminder_type)
        print(f"✅ Sent {reminder_type} work session reminder for {assignment_name} to user {user_id}")


async def send_due_date_reminders(channel: discord.TextChannel, now_utc: datetime):
    """Send reminders for upcoming assignment due dates."""
    if not channel.guild:
        return
    
    for member in channel.guild.members:
        if member.bot:
            continue
        
        user_id = str(member.id)
        due_reminders = await get_pending_due_date_reminders(now_utc, user_id)
        
        for reminder in due_reminders:
            assignment_id, course_id, assignment_name, due_at, course_code, course_name, reminder_type = reminder
            
            time_label = DUE_DATE_REMINDER_LABELS.get(reminder_type, '📅 Reminder')
            
            due_str = format_local(due_at, "%a %b %d, %I:%M %p") if due_at else "No due date"
            course_label = f"{course_code}: {course_name}" if course_code else course_name
            
            msg = f"{time_label} <@{user_id}>\n\n"
            msg += f"📝 **Assignment due soon:** {assignment_name}\n"
            msg += f"📖 **Course:** {course_label}\n"
            msg += f"⏳ **Due:** {due_str}\n\n"
            msg += DUE_DATE_REMINDER_MESSAGES.get(reminder_type, "")
            
            await channel.send(msg)
            await mark_due_date_reminder_sent(course_id, assignment_id, reminder_type)
            print(f"✅ Sent {reminder_type} due date reminder for {assignment_name} to user {user_id}")


async def check_and_send_completion_notifications(channel: discord.TextChannel):
    """Check if users have completed all weekly assignments and send congratulations."""
    if not channel.guild:
        return
    
    for member in channel.guild.members:
        if member.bot:
            continue
        
        user_id = str(member.id)
        today = datetime.now()
        monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
        
        # Skip if already notified this week
        if await get_week_completion_notified(user_id, monday):
            continue
        
        # Check completion status
        all_complete, total_count, completed_count = await check_week_completion(user_id, monday)
        
        if all_complete and total_count > 0:
            sunday = monday + timedelta(days=6)
            week_range = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')}"
            
            msg = f"🎉 **Congratulations!** <@{user_id}>\n\n"
            msg += f"✅ You've completed all {total_count} assignment(s) for the week of {week_range}!\n\n"
            msg += f"🌟 Great work staying on top of your coursework! Keep it up!\n\n"
            msg += f"💡 A new week will begin on Monday with fresh assignments."
            
            await channel.send(msg)
            await mark_week_completion_notified(user_id, monday)
            print(f"🎉 Sent week completion notification to user {user_id}")


# ========================================
# Bot Entry Point
# ========================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
