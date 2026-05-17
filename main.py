import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

COGS = ["cogs.setup", "cogs.queue", "cogs.tester", "cogs.appeal", "cogs.blacklist", "cogs.help"]

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    await bot.change_presence(
        activity=discord.Streaming(
            name="tier testing",
            url="https://twitch.tv/rankedtests"
        )
    )
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"  ✅ Loaded {cog}")
        except Exception as e:
            print(f"  ❌ Failed to load {cog}: {e}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

bot.run(os.getenv("TOKEN"))
