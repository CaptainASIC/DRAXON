import os
import certifi
import requests
from dotenv import load_dotenv
import discord
from discord import app_commands, Activity, ActivityType
from discord.ext import commands
import logging
import asyncio
from pathlib import Path

# Import configurations
from lib.constants import *

# Configure logging
LOG_DIR.mkdir(exist_ok=True)
ENV_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'DraXon_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DraXon_AI')

# Load environment variables
env_path = ENV_DIR / '.env'
load_dotenv(env_path)
TOKEN = os.getenv('DraXon_AI_TOKEN')

if not TOKEN:
    raise ValueError(f"No token found. Make sure to set DraXon_AI_TOKEN in {env_path}")

class DraXonAIBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(command_prefix='!', intents=intents)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        # Store for channel IDs
        self.incidents_channel_id = None
        self.promotion_channel_id = None
        self.demotion_channel_id = None
        self.reminder_channel_id = None
        self._ready = False
        
        logger.info("Bot initialized")

    async def setup_hook(self):
        """Initial setup when bot starts"""
        logger.info("Setup hook starting...")
        try:
            # Define all cogs to load
            cogs = [
                'cogs.channels',
                'cogs.status',
                'cogs.members',
                'cogs.promotion',
                'cogs.commands',
                'cogs.rsi_status_monitor',
                'cogs.rsi_incidents_monitor',
                'cogs.backup',
                'cogs.rsi_integration',
                'cogs.membership_monitor'
            ]
            
            # Load each cog only once
            for cog in cogs:
                try:
                    if cog not in self.extensions:
                        await self.load_extension(cog)
                        logger.info(f"Loaded {cog}")
                    else:
                        logger.info(f"Skipped loading {cog} (already loaded)")
                except Exception as e:
                    logger.error(f"Failed to load {cog}: {e}")
                    raise
            
            logger.info("All cogs loaded")
            
            await self.tree.sync()
            logger.info("Command tree synced")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            raise

    async def close(self):
        """Cleanup when bot shuts down"""
        logger.info("Bot shutting down, cleaning up...")
        self.session.close()
        await super().close()

bot = DraXonAIBot()

@bot.event
async def on_ready():
    if bot._ready:
        return
        
    logger.info(f'DraXon AI Bot v{APP_VERSION} has connected to Discord!')
    try:
        # Set custom activity with version number
        activity = discord.CustomActivity(
            name=f"Ver. {APP_VERSION} Processing..."
        )
        await bot.change_presence(activity=activity)
        logger.info("Bot activity status set successfully")
        
        # Mark as ready
        bot._ready = True
        
    except Exception as e:
        logger.error(f"Error in on_ready: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.errors.MissingRole):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing the command.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for application commands"""
    if isinstance(error, app_commands.errors.MissingRole):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True
        )
    else:
        logger.error(f"Application command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An error occurred while processing the command.",
                ephemeral=True
            )

if __name__ == "__main__":
    try:
        logger.info("Starting DraXon AI Bot...")
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise