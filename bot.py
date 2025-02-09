import os
import discord
from discord.ext import commands, tasks
import asyncio
from dotenv import load_dotenv
from flask import Flask
import threading
from datetime import datetime
import sqlite3

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Secure bot token
GUILD_ID = int(os.getenv("GUILD_ID"))  # Secure Guild ID
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID"))  # Secure Channel ID

# Define only necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message-based commands
intents.reactions = True  # Required for reaction-based interactions
intents.members = True  # Required for handling members in voice channels

bot = commands.Bot(command_prefix="!", intents=intents)

# Flask server to keep Render from shutting down
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# Start Flask in a separate thread
threading.Thread(target=run_web).start()

# Initialize database
conn = sqlite3.connect("sessions.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        creator_id INTEGER,
        date TEXT,
        time TEXT,
        duration INTEGER,
        max_participants INTEGER
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        session_id INTEGER,
        user_id INTEGER,
        FOREIGN KEY (session_id) REFERENCES sessions (id)
    )
""")
conn.commit()
conn.close()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def schedule(ctx, date: str, time: str, duration: int, max_participants: int):
    """Schedule a new study session and store it in the database."""
    try:
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not announcement_channel:
            await ctx.send("Error: Announcement channel not found!")
            return

        message = await announcement_channel.send(
            f'📅 **New Study Session Scheduled!** 📅\n'
            f'📆 **Date:** {date}\n'
            f'🕒 **Time:** {time}\n'
            f'⏳ **Duration:** {duration} minutes\n'
            f'👥 **Max Participants:** {max_participants}\n'
            f'✅ React to join!'
        )
        await message.add_reaction("✅")

        conn = sqlite3.connect("sessions.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sessions (message_id, creator_id, date, time, duration, max_participants) VALUES (?, ?, ?, ?, ?, ?)",
                       (message.id, ctx.author.id, date, time, duration, max_participants))
        conn.commit()
        conn.close()
    except Exception as e:
        await ctx.send(f"Error scheduling session: {e}")

@bot.command()
async def cancel_session(ctx, message_id: int):
    """Cancel a study session if the requester is the creator."""
    try:
        conn = sqlite3.connect("sessions.db")
        cursor = conn.cursor()
        cursor.execute("SELECT creator_id FROM sessions WHERE message_id = ?", (message_id,))
        session = cursor.fetchone()
        
        if not session:
            await ctx.send("Error: No such session found.")
            conn.close()
            return
        
        creator_id = session[0]
        if ctx.author.id != creator_id:
            await ctx.send("❌ You can only cancel sessions that you created!")
            conn.close()
            return
        
        cursor.execute("DELETE FROM sessions WHERE message_id = ?", (message_id,))
        cursor.execute("DELETE FROM participants WHERE session_id = ?", (message_id,))
        conn.commit()
        conn.close()
        await ctx.send(f"✅ Study session #{message_id} has been cancelled.")
    except Exception as e:
        await ctx.send(f"Error cancelling session: {e}")

@bot.command()
async def list_sessions(ctx):
    """List all scheduled study sessions."""
    conn = sqlite3.connect("sessions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, time, duration, max_participants FROM sessions")
    sessions = cursor.fetchall()
    conn.close()

    if not sessions:
        await ctx.send("📭 No scheduled study sessions found.")
        return

    message = "**📅 Upcoming Study Sessions:**\n"
    for session in sessions:
        session_id, date, time, duration, max_participants = session
        message += f"**#{session_id}** - 📆 {date} | 🕒 {time} | ⏳ {duration} min | 👥 {max_participants} max\n"

    await ctx.send(message)

bot.run(TOKEN)
