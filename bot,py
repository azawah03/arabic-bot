import os
import discord
from discord.ext import commands, tasks
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Secure bot token
GUILD_ID = int(os.getenv("GUILD_ID"))  # Secure Guild ID
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID"))  # Secure Channel ID

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
scheduled_sessions = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def schedule(ctx, time: str, duration: int, max_participants: int):
    """Schedule a new study session."""
    try:
        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not announcement_channel:
            await ctx.send("Error: Announcement channel not found!")
            return

        message = await announcement_channel.send(
            f'📅 **New Study Session Scheduled!** 📅\n'
            f'🕒 **Time:** {time}\n'
            f'⏳ **Duration:** {duration} minutes\n'
            f'👥 **Max Participants:** {max_participants}\n'
            f'✅ React to join!'
        )
        await message.add_reaction("✅")
        scheduled_sessions[message.id] = {
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
        await reaction.message.channel.send(f"✅ {user.mention} has joined the session!")
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
            name=f"Study Session {message_id}",
            overwrites=overwrites,
            category=None
        )
        session["voice_channel"] = voice_channel.id
        await ctx.send(f"✅ Voice channel created: {voice_channel.mention}")

        # Start monitoring for empty channel
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
