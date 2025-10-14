import discord
from discord.ext import commands
from config import BOT_TOKEN
from services.canvas_service import get_formatted_courses, get_formatted_assignments

# Define bot command prefix (e.g. !help, !ping)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

bot.run(BOT_TOKEN)
