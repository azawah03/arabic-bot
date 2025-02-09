import os
import discord
from discord.ext import commands, tasks
import asyncio
from dotenv import load_dotenv
from flask import Flask
import threading
from datetime import datetime

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
scheduled_sessions = {}
session_counter = 1  # Track session numbers

# Flask server to keep Render from shutting down
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# Start Flask in a separate thread
threading.Thread(target=run_web).start()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def schedule(ctx, date: str, time: str, duration: int, max_participants: int):
    """Schedule a new study session."""
    global session_counter
    try:
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not announcement_channel:
            await ctx.send("Error: Announcement channel not found!")
            return

        session_id = session_counter
        session_counter += 1

        message = await announcement_channel.send(
            f'📅 **Study Session #{session_id} Scheduled!** 📅\n'
            f'📆 **Date:** {date}\n'
            f'🕒 **Time:** {time}\n'
            f'⏳ **Duration:** {duration} minutes\n'
            f'👥 **Max Participants:** {max_participants}\n'
            f'✅ React to join!'
        )
        await message.add_reaction("✅")
        scheduled_sessions[message.id] = {
            "id": session_id,
            "date": date,
            "time": time,
            "duration": duration,
            "max_participants": max_participants,
            "participants": []
        }
    except Exception as e:
        await ctx.send(f"Error scheduling session: {e}")

@bot.event
async def on_reaction_add(reaction, user):
    """Handle user reactions to register for a session."""
    try:
        if user.bot:
            return
        
        message = await reaction.message.channel.fetch_message(reaction.message.id)  # Ensure message is fetched
        if message.id not in scheduled_sessions:
            return

        session = scheduled_sessions[message.id]
        if len(session["participants"]) >= session["max_participants"]:
            await reaction.message.channel.send(f"⚠️ {user.mention}, this session is full!")
            return

        session["participants"].append(user.id)
        await reaction.message.channel.send(f"✅ {user.mention} has joined Study Session #{session['id']}!")
    except Exception as e:
        print(f"Error handling reaction: {e}")

@bot.command()
async def start_session(ctx, message_id: int):
    """Start the study session and create a private voice channel."""
    try:
        if message_id not in scheduled_sessions:
            await ctx.send("Error: No such session found.")
            return

        session = scheduled_sessions[message_id]
        guild = bot.get_guild(GUILD_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        for user_id in session["participants"]:
            member = guild.get_member(user_id)
            if member:
                overwrites[member] = discord.PermissionOverwrite(view_channel=True, connect=True)

        voice_channel = await guild.create_voice_channel(
            name=f"Study Session #{session['id']}",
            overwrites=overwrites,
            category=None
        )
        session["voice_channel"] = voice_channel.id
        await ctx.send(f"✅ Voice channel created: {voice_channel.mention}")

        # Monitor for empty channel only after someone joins
        monitor_voice_channel.start(voice_channel.id)
    except Exception as e:
        await ctx.send(f"Error starting session: {e}")

@tasks.loop(seconds=30)
async def monitor_voice_channel(voice_channel_id):
    """Monitor voice channels and delete if empty."""
    try:
        guild = bot.get_guild(GUILD_ID)
        voice_channel = guild.get_channel(voice_channel_id)
        if voice_channel and len(voice_channel.members) == 0:
            await voice_channel.delete()
            monitor_voice_channel.stop()
    except Exception as e:
        print(f"Error deleting voice channel: {e}")

bot.run(TOKEN)
