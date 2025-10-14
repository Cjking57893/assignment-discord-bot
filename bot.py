import discord
from discord.ext import commands
from config import BOT_TOKEN
from database.db_manager import init_db
from services.canvas_service import get_formatted_courses, get_formatted_assignments
from utils.weekly import send_weekly_assignments
from utils.sync import sync_canvas_data

# Define bot command prefix (e.g. !help, !ping)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    await init_db()
    print("Database initialized.")
    print(f"✅ Logged in as {bot.user}")
    
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

bot.run(BOT_TOKEN)
