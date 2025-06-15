import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

# Initialize bot with Arabic-friendly settings
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None  # We'll create custom help
)

@bot.event
async def on_ready():
    print(f'{bot.user} قد اتصل بديسكورد!')
    print(f'Bot is in {len(bot.guilds)} servers')
    
    # Quick guild sync for immediate availability
    for guild in bot.guilds:
        try:
            synced = await bot.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands for guild {guild.name}')
        except Exception as e:
            print(f'Failed to sync for guild {guild.name}: {e}')

# Simple test command
@bot.tree.command(name="بينغ", description="اختبار سريع للبوت")
async def ping_test(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎉 البوت يعمل!",
        description=f"Ping: {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="اختبار_بسيط", description="اختبار آخر")
async def simple_test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ البوت جاهز ويعمل بشكل صحيح!")

if __name__ == "__main__":
    asyncio.run(bot.start(os.environ['DISCORD_BOT_TOKEN']))