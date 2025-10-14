import discord
from discord.ext import commands
from config import BOT_TOKEN
from database.db_manager import init_db, get_user_plans_for_week_detailed, get_week_assignments_with_status, set_assignment_completed
from services.canvas_service import get_formatted_courses, get_formatted_assignments
from utils.weekly import send_weekly_assignments
from utils.sync import sync_canvas_data
from utils.datetime_utils import format_local, get_local_tz

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

    # Filter to incomplete and not already submitted (submitted from Canvas)
    items = [r for r in rows if int(r[6]) == 0 and int(r[7]) == 0]  # completed idx=6, submitted idx=7

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
        return f"{i}. {assignment_name} — {label} (due {due_str})"

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

bot.run(BOT_TOKEN)
