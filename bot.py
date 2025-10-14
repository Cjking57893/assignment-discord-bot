import discord
from discord.ext import commands
from config import BOT_TOKEN
from database.db_manager import init_db, get_user_plans_for_week_detailed
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

bot.run(BOT_TOKEN)
