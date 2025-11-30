import discord
from discord.ext import commands, tasks
from config import BOT_TOKEN, CHANNEL_ID
from database.db_manager import (init_db, get_user_plans_for_week_detailed, get_week_assignments_with_status, 
                                 set_assignment_completed, get_pending_reminders, mark_reminder_sent, update_study_plan_time)
from services.canvas_service import get_formatted_courses, get_formatted_assignments
from utils.weekly import send_weekly_assignments, send_weekly_assignments_to_channel
from utils.sync import sync_canvas_data
from utils.datetime_utils import format_local, get_local_tz, to_utc_iso_z, parse_canvas_datetime
from datetime import time, datetime, timedelta

# Define bot command prefix (e.g. !help, !ping)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

_synced_once = False

@bot.event
async def on_ready():
    global _synced_once
    await init_db()
    print("Database initialized.")
    print(f"✅ Logged in as {bot.user}")
    # Auto-sync once when the bot is ready
    if not _synced_once:
        try:
            await sync_canvas_data()
            _synced_once = True
            print("Initial sync complete.")
        except Exception as e:
            print(f"Initial sync failed: {e}")
    
    # Start the weekly notification task
    if not weekly_notification.is_running():
        weekly_notification.start()
    
    # Start the reminder checking task
    if not check_reminders.is_running():
        check_reminders.start()
        print("⏰ Reminder system started.")
    
@bot.command()
async def sync(ctx):
    """Syncs the local database with your Canvas courses and assignments."""
    await ctx.send("🔄 Syncing Canvas data from Canvas API...")

    try:
        await sync_canvas_data()
        await ctx.send("✅ Sync complete! Local database updated.")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")

@bot.command()
async def thisweek(ctx):
    """List assignments due this week."""
    await send_weekly_assignments(ctx)


@bot.command()
async def plans(ctx):
    """List your planned study sessions for this week."""
    # Determine current week's Monday (local)
    from datetime import datetime, timedelta
    tz = get_local_tz()
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())

    # Fetch plans for user
    user_id = str(ctx.author.id)
    rows = await get_user_plans_for_week_detailed(user_id, monday)

    sunday = monday + timedelta(days=6)
    tz_label = tz.tzname(None) if hasattr(tz, 'tzname') else ''
    header_range = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')} ({tz_label})"

    if not rows:
        await ctx.send(f"You have no planned sessions for {header_range}. Use !thisweek to add some after listing assignments.")
        return

    # Format output
    lines = []
    for (assignment_id, course_id, planned_at_utc, notes, assignment_name, assignment_due_utc, course_code, course_name) in rows:
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
    Mark assignments as complete. If a query is provided, try to match assignments by name.
    Otherwise, list this week's incomplete assignments and let you pick by number (supports CSV like 1,3,5).
    """
    from datetime import datetime, timedelta
    from utils.datetime_utils import to_utc_iso_z
    tz = get_local_tz()
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())

    # Load this week's assignments with status
    user_id = str(ctx.author.id)
    rows = await get_week_assignments_with_status(user_id, monday)

    # Filter to not yet marked complete (regardless of Canvas submitted flag)
    items = [r for r in rows if int(r[6]) == 0]  # completed idx=6

    if query:
        q = query.lower()
        items = [r for r in items if q in (r[2] or '').lower()]
        if not items:
            await ctx.send("No matching incomplete assignments found for your query.")
            return

    if not items:
        await ctx.send("You have no incomplete assignments for this week. Nice!")
        return

    # Show a numbered list
    def fmt_row(i, r):
        assignment_id, course_id, assignment_name, due_utc, course_code, course_name, completed, submitted = r
        due_str = format_local(due_utc, "%a %b %d, %I:%M %p") if due_utc else "No due date"
        label = f"{course_code}: {course_name}" if course_code else course_name
        submitted_tag = " • submitted" if int(submitted) else ""
        return f"{i}. {assignment_name} — {label} (due {due_str}{submitted_tag})"

    listing = "\n".join(fmt_row(i+1, r) for i, r in enumerate(items))
    await ctx.send("Select the assignments to mark complete (e.g., '1,3,5'):\n" + listing)

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        m = await ctx.bot.wait_for('message', timeout=90.0, check=check_author)
    except Exception:
        await ctx.send("Timed out waiting for a selection.")
        return

    selection = m.content.strip()
    import re
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

    # Mark selected as completed now (UTC)
    now_local = datetime.now().astimezone(tz)
    now_utc_iso = to_utc_iso_z(now_local)
    count = 0
    for idx in picks:
        assignment_id, course_id, *_ = items[idx]
        await set_assignment_completed(user_id, int(course_id), int(assignment_id), True, now_utc_iso)
        count += 1

    await ctx.send(f"Marked {count} assignment(s) as completed.")


@tasks.loop(time=time(hour=9, minute=0))  # Run at 9:00 AM every day
async def weekly_notification():
    """Send weekly assignments notification every Monday at 9 AM."""
    from datetime import datetime
    
    # Check if today is Monday (weekday 0)
    if datetime.now().weekday() != 0:
        return
    
    # Sync Canvas data before sending the weekly update
    try:
        await sync_canvas_data()
        print("Weekly sync complete.")
    except Exception as e:
        print(f"Weekly sync failed: {e}")
    
    # Get the notification channel
    if not CHANNEL_ID:
        print("⚠️ CHANNEL_ID not configured. Skipping weekly notification.")
        return
    
    try:
        channel_id = int(CHANNEL_ID)
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"⚠️ Could not find channel with ID {channel_id}")
            return
        
        # Send the weekly assignments to the channel
        await send_weekly_assignments_to_channel(channel)
        print("📅 Weekly Monday scheduling message sent!")
    except ValueError:
        print(f"⚠️ Invalid CHANNEL_ID: {CHANNEL_ID}")
    except Exception as e:
        print(f"❌ Error sending weekly notification: {e}")


@tasks.loop(minutes=1)  # Check every minute for reminders
async def check_reminders():
    """Check for pending reminders and send them."""
    if not CHANNEL_ID:
        return
    
    try:
        channel_id = int(CHANNEL_ID)
        channel = bot.get_channel(channel_id)
        if not channel:
            return
        
        # Get current time in UTC
        now_utc = datetime.now(datetime.now().astimezone().tzinfo).astimezone(datetime.now().astimezone().tzinfo.utc if hasattr(datetime.now().astimezone().tzinfo, 'utc') else None)
        if now_utc.tzinfo is None:
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
        else:
            now_utc = datetime.utcnow().replace(tzinfo=datetime.now().astimezone().tzinfo.utc if hasattr(datetime.now().astimezone().tzinfo, 'utc') else None)
        
        # Simpler approach
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        
        # Get pending reminders
        reminders = await get_pending_reminders(now_utc)
        
        for reminder in reminders:
            user_id, course_id, assignment_id, planned_at_utc, assignment_name, due_at, course_code, course_name, reminder_type = reminder
            
            # Format the reminder message
            time_labels = {
                '24h': '⏰ **24-hour reminder**',
                '1h': '⏰ **1-hour reminder**',
                'now': '🔔 **It\'s time!**'
            }
            time_label = time_labels.get(reminder_type, '⏰ Reminder')
            
            planned_local = format_local(planned_at_utc, "%a %b %d, %I:%M %p")
            due_str = format_local(due_at, "%a %b %d, %I:%M %p") if due_at else "No due date"
            course_label = f"{course_code}: {course_name}" if course_code else course_name
            
            # Mention the user
            user_mention = f"<@{user_id}>"
            
            msg = f"{time_label} {user_mention}\n\n"
            msg += f"📚 **Planned work session for:** {assignment_name}\n"
            msg += f"📖 **Course:** {course_label}\n"
            msg += f"🕒 **Scheduled time:** {planned_local}\n"
            msg += f"⏳ **Due:** {due_str}\n\n"
            msg += f"💡 Reply with `!reschedule` to change the time for this session."
            
            await channel.send(msg)
            
            # Mark reminder as sent
            await mark_reminder_sent(user_id, course_id, assignment_id, reminder_type)
            print(f"✅ Sent {reminder_type} reminder for {assignment_name} to user {user_id}")
            
    except Exception as e:
        print(f"❌ Error checking reminders: {e}")


@bot.command()
async def reschedule(ctx):
    """Reschedule a planned work session."""
    # Get user's current week plans
    from datetime import datetime, timedelta
    tz = get_local_tz()
    today = datetime.now()
    monday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    
    user_id = str(ctx.author.id)
    rows = await get_user_plans_for_week_detailed(user_id, monday)
    
    if not rows:
        await ctx.send("You have no planned sessions to reschedule. Use !thisweek to create some.")
        return
    
    # Show numbered list
    lines = []
    for i, (assignment_id, course_id, planned_at_utc, notes, assignment_name, assignment_due_utc, course_code, course_name) in enumerate(rows, 1):
        planned_local = format_local(planned_at_utc, "%a %b %d, %I:%M %p")
        course_label = f"{course_code}: {course_name}" if course_code else course_name
        lines.append(f"{i}. {assignment_name} — {course_label} (scheduled {planned_local})")
    
    await ctx.send("Which session do you want to reschedule? Enter the number:\n" + "\n".join(lines))
    
    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        selection_msg = await ctx.bot.wait_for('message', timeout=60.0, check=check_author)
    except Exception:
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
    
    await ctx.send(f"Enter the new time for **{assignment_name}** (e.g., 'Wed 7:30 PM'):")
    
    try:
        time_msg = await ctx.bot.wait_for('message', timeout=120.0, check=check_author)
    except Exception:
        await ctx.send("Timed out waiting for new time.")
        return
    
    # Parse the time (reuse logic from weekly.py)
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
    match = re.match(r"^\s*([A-Za-z]+)\s+(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*$", time_msg.content)
    if not match:
        await ctx.send("Sorry, I didn't understand. Please use format like 'Wed 7:30 PM'.")
        return
    
    day_str, hh, mm, ap = match.groups()
    day_idx = day_map.get(day_str.lower())
    if day_idx is None:
        await ctx.send("Unknown day. Try Mon/Tue/Wed/Thu/Fri/Sat/Sun.")
        return
    
    hour = int(hh) % 12
    if ap.lower() == 'pm':
        hour += 12
    minute = int(mm)
    
    new_planned_local = monday + timedelta(days=day_idx)
    new_planned_local = new_planned_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    new_planned_local = new_planned_local.replace(tzinfo=get_local_tz())
    new_planned_utc_iso = to_utc_iso_z(new_planned_local)
    
    # Update the database
    await update_study_plan_time(user_id, course_id, assignment_id, new_planned_utc_iso)
    
    await ctx.send(f"✅ Rescheduled **{assignment_name}** to {new_planned_local.strftime('%a %b %d at %I:%M %p')}. Reminders have been reset.")


bot.run(BOT_TOKEN)
