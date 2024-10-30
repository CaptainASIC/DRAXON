import os
import certifi
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import ssl
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Setup directories
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
ENV_DIR = BASE_DIR / "env"

# Create directories if they don't exist
LOG_DIR.mkdir(exist_ok=True)
ENV_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'pulse_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PULSE')

# Set OpenSSL environment variable
os.environ['CRYPTOGRAPHY_OPENSSL_NO_LEGACY'] = '1'

# Load environment variables from env directory
env_path = ENV_DIR / '.env'
load_dotenv(env_path)
TOKEN = os.getenv('DISCORD_TOKEN')
COOLDOWN_MINUTES = int(os.getenv('COOLDOWN_MINUTES', '5'))

if not TOKEN:
    raise ValueError(f"No token found. Make sure to set DISCORD_TOKEN in {env_path}")

# Create SSL context with proper certificate verification
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Bot setup with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Define DraXon role hierarchy
DraXon_ROLES = {
    'leadership': ['Chairman', 'Director'],
    'management': ['Manager', 'Team Leader'],
    'staff': ['Employee', 'Applicant'],
    'restricted': ['Applicant']
}

class PULSEBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.ssl_context = ssl_context
        self.sos_cooldowns = {}  # Track user cooldowns
        self.alert_channel_id = None  # Store the channel ID for alerts

    async def setup_hook(self):
        logger.info("Bot is setting up...")

bot = PULSEBot()

def check_cooldown(user_id: int) -> tuple[bool, float]:
    """Check if a user is on cooldown. Returns (is_on_cooldown, time_remaining)"""
    if user_id in bot.sos_cooldowns:
        elapsed = (datetime.now() - bot.sos_cooldowns[user_id]).total_seconds()
        if elapsed < COOLDOWN_MINUTES * 60:
            return True, (COOLDOWN_MINUTES * 60) - elapsed
    return False, 0

class SOSModal(discord.ui.Modal, title='PULSE Emergency Alert'):
    def __init__(self):
        super().__init__(timeout=None)
        self.location = discord.ui.TextInput(
            label='What is your current location?',
            placeholder='Enter your location here...',
            required=True,
            max_length=100
        )
        self.reason = discord.ui.TextInput(
            label='Emergency Description',
            placeholder='Briefly describe your emergency situation...',
            required=True,
            max_length=200,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.location)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        location = self.location.value
        reason = self.reason.value

        if not bot.alert_channel_id:
            await interaction.response.send_message(
                "⚠️ Alert channel has not been configured. Please contact a Chairman.",
                ephemeral=True
            )
            return

        # Set cooldown
        bot.sos_cooldowns[user.id] = datetime.now()

        channel = bot.get_channel(bot.alert_channel_id)
        if not channel:
            logger.error(f"Alert channel not found: {bot.alert_channel_id}")
            await interaction.response.send_message(
                "⚠️ Alert channel not found. Please contact a Chairman.",
                ephemeral=True
            )
            return

        try:
            # Create the alert message
            alert_message = await channel.send(
                f"🚨 **PULSE EMERGENCY ALERT** 🚨\n\n"
                f"**Alert from:** {user.mention}\n"
                f"**Location:** {location}\n"
                f"**Situation:** {reason}\n\n"
                f"*This is a priority alert from the PULSE system*"
            )

            # Create a thread for this emergency
            thread = await alert_message.create_thread(
                name=f"Emergency: {user.name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                auto_archive_duration=1440  # 24 hours
            )

            # Send initial thread message
            await thread.send(
                f"Emergency thread created for {user.mention}'s alert.\n"
                f"Please use this thread to coordinate response efforts."
            )

            logger.info(f"SOS from {user.name} posted to channel {channel.name} with thread created")

            await interaction.response.send_message(
                f"🚨 Emergency alert posted successfully.\n"
                f"A thread has been created to track this emergency.\n"
                f"Please monitor the alert channel for responses.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Failed to post alert: {e}")
            await interaction.response.send_message(
                "Failed to post emergency alert. Please try again or contact an administrator.",
                ephemeral=True
            )

@bot.event
async def on_ready():
    logger.info(f'PULSE Bot has connected to Discord!')
    try:
        # Set custom activity without prefix
        activity = discord.CustomActivity(
            name="Planetary & Universal Locator System for Emergencies"
        )
        await bot.change_presence(activity=activity)
        logger.info("Bot activity status set successfully")

        # Sync commands
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to setup bot: {e}")

@bot.tree.command(name="setup", description="Configure the PULSE alert channel")
@app_commands.checks.has_role("Chairman")
@app_commands.describe(channel="Select the channel for emergency alerts")
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set up the channel for PULSE alerts"""
    try:
        # Save the channel ID
        bot.alert_channel_id = channel.id
        
        # Test permissions
        permissions = channel.permissions_for(interaction.guild.me)
        missing_permissions = []
        
        if not permissions.send_messages:
            missing_permissions.append("Send Messages")
        if not permissions.create_public_threads:
            missing_permissions.append("Create Public Threads")
        if not permissions.send_messages_in_threads:
            missing_permissions.append("Send Messages in Threads")

        if missing_permissions:
            await interaction.response.send_message(
                f"⚠️ Warning: Missing permissions in {channel.mention}:\n"
                f"Missing: {', '.join(missing_permissions)}\n"
                f"Please grant these permissions for full functionality.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ PULSE alert channel configured successfully!\n"
            f"Channel: {channel.mention}\n"
            f"All emergency alerts will be posted here.",
            ephemeral=True
        )
        
        # Send test message to channel
        await channel.send(
            "🔧 **PULSE System Configuration**\n"
            "This channel has been configured for PULSE emergency alerts.\n"
            "Each alert will create a new thread for coordination."
        )
        
        logger.info(f"Alert channel configured to #{channel.name} ({channel.id}) by {interaction.user.name}")
    
    except Exception as e:
        logger.error(f"Failed to configure alert channel: {e}")
        await interaction.response.send_message(
            "⚠️ Failed to configure alert channel. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="sos", description="Send an emergency alert to DraXon staff")
async def sos(interaction: discord.Interaction):
    # Check if user has appropriate role
    user_roles = [role.name for role in interaction.user.roles]
    
#    if any(role in DraXon_ROLES['restricted'] for role in user_roles):
#        logger.warning(f"User {interaction.user.name} (Applicant) attempted to use SOS")
#        await interaction.response.send_message(
#            "⚠️ Applicants cannot use the emergency alert system.", 
#            ephemeral=True
#       )
#        return

    if not any(role in [*DraXon_ROLES['leadership'], *DraXon_ROLES['management'], *DraXon_ROLES['staff']] 
               for role in user_roles):
        logger.warning(f"User {interaction.user.name} attempted to use SOS without proper role")
        await interaction.response.send_message(
            "⚠️ You must be an DraXon employee to use the emergency alert system.", 
            ephemeral=True
        )
        return

    # Check if alert channel is configured
    if not bot.alert_channel_id:
        await interaction.response.send_message(
            "⚠️ Alert channel has not been configured. Please contact a Chairman.",
            ephemeral=True
        )
        return

    # Check cooldown
    on_cooldown, time_remaining = check_cooldown(interaction.user.id)
    if on_cooldown:
        logger.info(f"User {interaction.user.name} attempted to use SOS while on cooldown")
        await interaction.response.send_message(
            f"⚠️ Please wait {int(time_remaining)} seconds before sending another alert.", 
            ephemeral=True
        )
        return

    # Create and send modal
    try:
        modal = SOSModal()
        await interaction.response.send_modal(modal)
    except Exception as e:
        logger.error(f"Failed to send modal: {e}")
        try:
            await interaction.response.send_message(
                "Failed to create emergency alert form. Please try again or contact an administrator.",
                ephemeral=True
            )
        except Exception as modal_e:
            logger.error(f"Failed to send error message: {modal_e}")

@bot.tree.command(name="pulse-status", description="Check PULSE system status")
@app_commands.checks.has_role("Chairman")
async def pulse_status(interaction: discord.Interaction):
    """Command to check bot status and statistics"""
    uptime = datetime.now() - datetime.fromtimestamp(bot.user.created_at.timestamp())
    
    # Get alert channel info
    alert_channel = bot.get_channel(bot.alert_channel_id) if bot.alert_channel_id else None
    
    # Count all members
    total_members = 0
    role_counts = {}

    for category, roles in DraXon_ROLES.items():
        for role_name in roles:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                members = len([m for m in role.members if not m.bot])
                role_counts[role_name] = members
                total_members += members

    # Format role breakdown
    role_breakdown = "\n".join(f"└ {role}: {count}" for role, count in role_counts.items())

    await interaction.response.send_message(
        f"📊 **PULSE System Status**\n"
        f"System Online: ✅\n"
        f"Uptime: {uptime.days} days, {uptime.seconds//3600} hours\n\n"
        f"👥 **Staff Breakdown:**\n{role_breakdown}\n"
        f"Total Members: {total_members}\n\n"
        f"⚙️ **System Configuration:**\n"
        f"└ Alert Channel: {alert_channel.mention if alert_channel else 'Not Configured'}\n"
        f"└ Alert Cooldown: {COOLDOWN_MINUTES} minutes",
        ephemeral=True
    )

if __name__ == "__main__":
    try:
        logger.info("Starting PULSE Bot...")
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")