import discord
from discord import app_commands
from discord.ext import commands
import logging
from lib.constants import DraXon_ROLES, STATUS_EMOJIS, APP_VERSION

logger = logging.getLogger('DraXon_AI')

class ChannelSelectView(discord.ui.View):
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.incidents_channel = None
        self.promotion_channel = None
        self.demotion_channel = None
        self.reminder_channel = None

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Incidents Channel",
        min_values=1,
        max_values=1
    )
    async def incidents_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.incidents_channel = select.values[0]
        select.disabled = True
        select.placeholder = f"Incidents Channel: {self.incidents_channel.name}"
        await self.check_completion(interaction)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Promotion Channel",
        min_values=1,
        max_values=1
    )
    async def promotion_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.promotion_channel = select.values[0]
        select.disabled = True
        select.placeholder = f"Promotion Channel: {self.promotion_channel.name}"
        await self.check_completion(interaction)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Demotion Channel",
        min_values=1,
        max_values=1
    )
    async def demotion_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.demotion_channel = select.values[0]
        select.disabled = True
        select.placeholder = f"Demotion Channel: {self.demotion_channel.name}"
        await self.check_completion(interaction)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Reminder Channel",
        min_values=1,
        max_values=1
    )
    async def reminder_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.reminder_channel = select.values[0]
        select.disabled = True
        select.placeholder = f"Reminder Channel: {self.reminder_channel.name}"
        await self.check_completion(interaction)

    @discord.ui.button(label="Reset Selections", style=discord.ButtonStyle.secondary)
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset all selections"""
        for child in self.children:
            if isinstance(child, discord.ui.ChannelSelect):
                child.disabled = False
                child.placeholder = child.placeholder.split(":")[0]
        
        self.incidents_channel = None
        self.promotion_channel = None
        self.demotion_channel = None
        self.reminder_channel = None
        
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Confirm Setup", style=discord.ButtonStyle.green, disabled=True)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Process the final setup"""
        try:
            # Store channel IDs in bot
            self.bot.incidents_channel_id = self.incidents_channel.id
            self.bot.promotion_channel_id = self.promotion_channel.id
            self.bot.demotion_channel_id = self.demotion_channel.id
            self.bot.reminder_channel_id = self.reminder_channel.id

            # Create confirmation embed
            embed = discord.Embed(
                title="✅ Setup Complete",
                description="Channel configuration has been updated:",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Channel Assignments",
                value=f"📢 Incidents: {self.incidents_channel.mention}\n"
                      f"🎉 Promotions: {self.promotion_channel.mention}\n"
                      f"🔄 Demotions: {self.demotion_channel.mention}\n"
                      f"📋 Reminders: {self.reminder_channel.mention}",
                inline=False
            )

            # Disable all components
            for child in self.children:
                child.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Error in setup confirmation: {e}")
            await interaction.response.send_message(
                "❌ An error occurred during setup. Please try again.",
                ephemeral=True
            )

    async def check_completion(self, interaction: discord.Interaction):
        """Check if all channels have been selected"""
        all_selected = all([
            self.incidents_channel,
            self.promotion_channel,
            self.demotion_channel,
            self.reminder_channel
        ])
        
        # Enable/disable confirm button based on completion
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == "Confirm Setup":
                child.disabled = not all_selected
        
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        """Handle timeout by disabling all components"""
        for child in self.children:
            child.disabled = True

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="draxon-stats", description="Display DraXon member statistics")
    @app_commands.checks.has_any_role("Chairman", "Director")
    async def draxon_stats(self, interaction: discord.Interaction):
        """Command to display member statistics"""
        try:
            total_members = 0
            role_counts = {}
            
            for category, roles in DraXon_ROLES.items():
                for role_name in roles:
                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                    if role:
                        members = len([m for m in role.members if not m.bot])
                        role_counts[role_name] = members
                        total_members += members

            bot_role = discord.utils.get(interaction.guild.roles, name="Bots")
            bot_count = len(bot_role.members) if bot_role else 0

            role_breakdown = "\n".join(f"└ {role}: {count}" 
                                     for role, count in role_counts.items())

            await interaction.response.send_message(
                f"📊 **DraXon Member Statistics**\n\n"
                f"👥 **Member Breakdown:**\n{role_breakdown}\n\n"
                f"Total Human Members: {total_members}\n"
                f"Total Automated Systems: {bot_count}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching statistics.",
                ephemeral=True
            )

    @app_commands.command(name="refresh-channels", description="Manually refresh DraXon AI channels")
    @app_commands.checks.has_role("Chairman")
    async def refresh_channels(self, interaction: discord.Interaction):
        """Manually trigger channel refresh"""
        try:
            members_cog = self.bot.get_cog('MembersCog')
            status_cog = self.bot.get_cog('StatusCog')
            
            if not members_cog or not status_cog:
                await interaction.response.send_message(
                    "❌ Required cogs not found.",
                    ephemeral=True
                )
                return
                
            await members_cog.update_member_counts()
            await status_cog.update_server_status()
            await interaction.response.send_message(
                "✅ Channels refreshed successfully!", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error refreshing channels: {e}")
            await interaction.response.send_message(
                "❌ Failed to refresh channels. Check logs for details.", 
                ephemeral=True
            )

    @app_commands.command(name="system-status", description="Display current system statuses")
    async def system_status(self, interaction: discord.Interaction):
        """Display current system statuses"""
        status_monitor = self.bot.get_cog('RSIStatusMonitorCog')
        if not status_monitor:
            await interaction.response.send_message(
                "❌ Status monitor not available.",
                ephemeral=True
            )
            return
            
        status_messages = []
        for system, status in status_monitor.system_statuses.items():
            emoji = STATUS_EMOJIS.get(status, '❓')
            system_name = system.replace('-', ' ').title()
            status_messages.append(f"{emoji} **{system_name}**: {status.title()}")

        await interaction.response.send_message(
            "🖥️ **Current System Status**\n\n" + "\n".join(status_messages),
            ephemeral=True
        )

    @app_commands.command(name="setup", description="Configure bot channels")
    @app_commands.checks.has_role("Chairman")
    async def setup(self, interaction: discord.Interaction):
        """Setup command using channel selection view"""
        try:
            embed = discord.Embed(
                title="DraXon AI Channel Setup",
                description="Please select the channels for each notification type below.\n"
                           "All channels must be selected before confirming the setup.",
                color=discord.Color.blue()
            )
            
            view = ChannelSelectView(self.bot)
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in setup command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while initializing setup.",
                ephemeral=True
            )

    @app_commands.command(name="force-check", description="Force check for new incidents and status")
    @app_commands.checks.has_role("Chairman")
    async def force_check(self, interaction: discord.Interaction):
        """Manually trigger status and incident checks"""
        try:
            status_monitor = self.bot.get_cog('RSIStatusMonitorCog')
            incident_monitor = self.bot.get_cog('RSIIncidentMonitorCog')
            
            if not status_monitor or not incident_monitor:
                await interaction.response.send_message(
                    "❌ Required monitors not available.",
                    ephemeral=True
                )
                return
                
            await status_monitor.check_status()
            await incident_monitor.check_incidents()
            await interaction.response.send_message(
                "✅ Manual check completed successfully!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in force check: {e}")
            await interaction.response.send_message(
                "❌ Error during manual check. Check logs for details.",
                ephemeral=True
            )

    @app_commands.command(name="help", description="Display available DraXon AI commands")
    async def help_command(self, interaction: discord.Interaction):
        """Display help information for all commands"""
        user_roles = [role.name for role in interaction.user.roles]
        is_leadership = any(role in DraXon_ROLES['leadership'] for role in user_roles)

        embed = discord.Embed(
            title=f"DraXon AI Commands v{APP_VERSION}",
            description="Available commands and their descriptions:",
            color=discord.Color.blue()
        )

        # Basic commands section
        basic_commands = [
            ("/system-status", "Display current status of RSI systems"),
            ("/draxon-link", "Link your RSI account with Discord"),
            ("/help", "Display this help message")
        ]
        
        embed.add_field(
            name="📌 Basic Commands",
            value="\n".join(f"`{cmd}`: {desc}" for cmd, desc in basic_commands),
            inline=False
        )
        
        if is_leadership:
            # Leadership commands section
            leadership_commands = [
                ("/draxon-stats", "Display detailed member statistics"),
                ("/promote", "Promote a member with role selection"),
                ("/demote", "Demote a member with role selection")
            ]

            embed.add_field(
                name="👥 Leadership Commands",
                value="\n".join(f"`{cmd}`: {desc}" for cmd, desc in leadership_commands),
                inline=False
            )

            if "Chairman" in user_roles:
                # Chairman-only commands section
                chairman_commands = [
                    ("/draxon-org", "View organization member list"),
                    ("/draxon-compare", "Compare Discord and RSI members"),
                    ("/refresh-channels", "Manually refresh channels"),
                    ("/setup", "Configure bot channels and notifications"),
                    ("/force-check", "Force status checks"),
                    ("/draxon-backup", "Create server backup"),
                    ("/draxon-restore", "Restore from backup")
                ]
                
                embed.add_field(
                    name="⚡ Chairman Commands",
                    value="\n".join(f"`{cmd}`: {desc}" for cmd, desc in chairman_commands),
                    inline=False
                )

        # New features section
        embed.add_field(
            name="🆕 New Features v1.6.1",
            value="• Enhanced promotion and demotion system with role selection\n"
                  "• Improved setup process with channel selection\n"
                  "• Better error prevention in configuration\n"
                  "• Streamlined notification management\n"
                  "• Added reason tracking for rank changes",
            inline=False
        )

        embed.set_footer(text=f"DraXon AI v{APP_VERSION} - Use commands in appropriate channels")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Safe setup function for commands cog"""
    try:
        if not bot.get_cog('CommandsCog'):
            await bot.add_cog(CommandsCog(bot))
            logger.info('Commands cog loaded successfully')
        else:
            logger.info('Commands cog already loaded, skipping')
    except Exception as e:
        logger.error(f'Error loading commands cog: {e}')
        raise