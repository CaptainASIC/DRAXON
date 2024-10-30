import discord
from discord.ext import commands
import logging
import asyncio
from lib.constants import (
    CATEGORY_NAME, 
    CHANNELS_CONFIG, 
    BOT_REQUIRED_PERMISSIONS, 
    CHANNEL_PERMISSIONS,
    STATUS_EMOJIS
)

logger = logging.getLogger('DraXon_AI')

class ChannelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.category = None
        self._channels_created = False
        self._setup_complete = False

    def log_permission_details(self, guild):
        """Log detailed permission information"""
        try:
            logger.info(f"=== Permission Details for {guild.name} ===")
            logger.info(f"Bot's name: {guild.me.name}")
            logger.info(f"Bot's top role: {guild.me.top_role.name}")
            logger.info(f"Bot's role position: {guild.me.top_role.position}")
            logger.info(f"Server owner: {guild.owner}")
            logger.info("Role Hierarchy:")
            for role in reversed(guild.roles):
                logger.info(f"- {role.name} (Position: {role.position})")
            logger.info("=== End Permission Details ===")
        except Exception as e:
            logger.error(f"Error logging permission details: {e}")

    async def check_bot_permissions(self, guild):
        """Check if bot has required permissions in the guild"""
        try:
            permissions = guild.me.guild_permissions
            logger.info(f"Checking bot permissions in {guild.name}")
            
            # Log detailed permission state
            self.log_permission_details(guild)
            
            # Check if bot can manage roles and is high enough in hierarchy
            can_manage_roles = all([
                permissions.manage_roles,
                guild.me.top_role.position > 1,  # Above @everyone
                permissions.manage_channels
            ])

            if not can_manage_roles:
                logger.error("Bot cannot manage roles effectively:")
                logger.error(f"- Can manage roles: {permissions.manage_roles}")
                logger.error(f"- Role position: {guild.me.top_role.position}")
                logger.error(f"- Can manage channels: {permissions.manage_channels}")
                return False, ["Insufficient role management permissions"]

            missing_permissions = []
            for perm in BOT_REQUIRED_PERMISSIONS:
                if not getattr(permissions, perm):
                    missing_permissions.append(perm)

            if missing_permissions:
                logger.error(f"Missing permissions: {', '.join(missing_permissions)}")
                return False, missing_permissions

            return True, []

        except Exception as e:
            logger.error(f"Error during permission check: {e}")
            return False, ["Error checking permissions"]

    async def get_category(self, guild):
        """Get existing category if it exists"""
        # If we already have a valid category, return it
        if self.category and self.category in guild.categories:
            return self.category
        
        # Reset category if it's not valid anymore
        self.category = None
        
        # Look for existing category
        existing_categories = [c for c in guild.categories if c.name == CATEGORY_NAME]
        if existing_categories:
            # Use the first category found
            self.category = existing_categories[0]
            logger.info(f"Found existing category: {self.category.name}")
            
            # Clean up any duplicates if they exist
            if len(existing_categories) > 1:
                logger.warning(f"Found {len(existing_categories)} duplicate categories. Cleaning up...")
                for category in existing_categories[1:]:
                    try:
                        await category.delete()
                        logger.info(f"Deleted duplicate category: {category.name}")
                    except Exception as e:
                        logger.error(f"Failed to delete duplicate category: {e}")
            
            return self.category
        
        return None

    def get_channel_name(self, config, count=None, status=None):
        """Generate channel name based on configuration"""
        if config["count_type"] == "status":
            emoji = STATUS_EMOJIS.get(status, '❓')
            return config["display"].format(emoji=emoji)
        else:
            return config["display"].format(count=count)

    async def setup_guild(self, guild):
        """Setup channels for a guild during initial bot startup"""
        logger.info(f"Setting up guild: {guild.name}")
        
        # Check permissions first
        has_perms, missing_perms = await self.check_bot_permissions(guild)
        if not has_perms:
            logger.error(f"Cannot setup channels in {guild.name}")
            logger.error("Required Permissions:")
            for perm in BOT_REQUIRED_PERMISSIONS:
                logger.error(f"- {perm}")
            logger.error("Missing Permissions:")
            for perm in missing_perms:
                logger.error(f"- {perm}")
            return
        
        try:
            # Get or create category (only during initial setup)
            category = await self.get_category(guild)
            if not category:
                # Create category with permissions
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        **CHANNEL_PERMISSIONS['display_only']['everyone']
                    ),
                    guild.me: discord.PermissionOverwrite(
                        **CHANNEL_PERMISSIONS['display_only']['bot']
                    )
                }
                
                category = await guild.create_category(
                    name=CATEGORY_NAME,
                    overwrites=overwrites,
                    reason="DraXon AI Bot Category Creation"
                )
                self.category = category
                logger.info(f"Created new category in {guild.name}")

            # Create initial channels
            for config in CHANNELS_CONFIG:
                base_name = config["name"].lower()
                if not any(ch.name.lower().startswith(base_name) for ch in category.voice_channels):
                    try:
                        initial_name = self.get_channel_name(
                            config,
                            count=0 if config["count_type"] in ["members", "bots"] else None,
                            status='operational' if config["count_type"] == "status" else None
                        )
                        
                        # Create channel with permissions from constants
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(
                                **CHANNEL_PERMISSIONS['display_only']['everyone']
                            ),
                            guild.me: discord.PermissionOverwrite(
                                **CHANNEL_PERMISSIONS['display_only']['bot']
                            )
                        }
                        
                        channel = await category.create_voice_channel(
                            name=initial_name,
                            overwrites=overwrites,
                            reason="DraXon AI Bot Channel Creation"
                        )
                        logger.info(f"Created channel {initial_name}")
                    except Exception as e:
                        logger.error(f"Failed to create channel {base_name}: {e}")

            # Trigger initial updates
            try:
                members_cog = self.bot.get_cog('MembersCog')
                status_cog = self.bot.get_cog('StatusCog')
                
                if members_cog:
                    await members_cog.update_member_counts()
                if status_cog:
                    await status_cog.update_server_status()
                
                logger.info("Initial channel updates completed")
            except Exception as e:
                logger.error(f"Error during initial channel updates: {e}")

        except Exception as e:
            logger.error(f"Error during guild setup: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Handle initial channel setup when bot is ready"""
        if self._setup_complete:
            return
            
        await self.bot.wait_until_ready()
        logger.info("Starting channel setup...")
        await asyncio.sleep(1)  # Brief delay to ensure everything is ready
        
        for guild in self.bot.guilds:
            await self.setup_guild(guild)
        
        self._setup_complete = True
        self._channels_created = True
        logger.info("All channel setup completed")

    @commands.command(name="fix-permissions")
    @commands.has_role("Chairman")
    async def fix_permissions(self, ctx):
        """Fix permissions for all DraXon AI channels"""
        try:
            guild = ctx.guild
            has_perms, missing_perms = await self.check_bot_permissions(guild)
            if not has_perms:
                await ctx.send("❌ Bot is missing required permissions: " + ", ".join(missing_perms))
                return

            category = await self.get_category(guild)
            if not category:
                await ctx.send("❌ Could not find DraXon AI category.")
                return

            await ctx.send("🔄 Fixing channel permissions...")

            # Update category permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    **CHANNEL_PERMISSIONS['display_only']['everyone']
                ),
                guild.me: discord.PermissionOverwrite(
                    **CHANNEL_PERMISSIONS['display_only']['bot']
                )
            }

            await category.edit(overwrites=overwrites)

            # Update each channel's permissions
            for channel in category.voice_channels:
                await channel.edit(overwrites=overwrites)

            await ctx.send("✅ Successfully updated all channel permissions!")

        except Exception as e:
            logger.error(f"Error fixing permissions: {e}")
            await ctx.send("❌ An error occurred while updating permissions.")

async def setup(bot):
    await bot.add_cog(ChannelsCog(bot))