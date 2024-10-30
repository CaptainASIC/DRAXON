import discord
from discord import app_commands
from discord.ext import commands
import logging
from lib.constants import DraXon_ROLES, STATUS_EMOJIS, APP_VERSION

logger = logging.getLogger('DraXon_AI')

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="draxon-stats", description="Display DraXon member statistics")
    async def draxon_stats(self, interaction: discord.Interaction):
        """Command to display member statistics"""
        user_roles = [role.name for role in interaction.user.roles]
        
        if not any(role in DraXon_ROLES['leadership'] for role in user_roles):
            await interaction.response.send_message(
                "⚠️ You do not have permission to view member statistics.", 
                ephemeral=True
            )
            return

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
    async def setup(
        self, 
        interaction: discord.Interaction, 
        incidents_channel: discord.TextChannel,
        promotion_channel: discord.TextChannel
    ):
        """Setup command to configure the channels"""
        self.bot.incidents_channel_id = incidents_channel.id
        self.bot.promotion_channel_id = promotion_channel.id
        
        await interaction.response.send_message(
            f"✅ Configuration updated:\n"
            f"• Incidents will be posted to {incidents_channel.mention}\n"
            f"• Promotions will be announced in {promotion_channel.mention}",
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
            title="DraXon AI Commands",
            description="Available commands and their descriptions:",
            color=discord.Color.blue()
        )

        # Basic commands
        basic_commands = [
            ("/system-status", "Display current status of RSI systems"),
            ("/draxon-link", "Link your RSI account with Discord"),
            ("/draxon-org", "Display organization member list with roles"),
            ("/draxon-compare", "Compare Discord members with RSI org members")
        ]
        
        for cmd_name, cmd_desc in basic_commands:
            embed.add_field(
                name=cmd_name,
                value=cmd_desc,
                inline=False
            )
        
        if is_leadership:
            # Leadership commands
            embed.add_field(
                name="/draxon-stats",
                value="Display detailed member statistics",
                inline=False
            )

            if "Chairman" in user_roles:
                # Chairman-only commands
                chairman_commands = [
                    ("/refresh-channels", "Manually refresh all DraXon AI channels"),
                    ("/setup", "Configure bot channels for incidents and promotions"),
                    ("/force-check", "Force check for new incidents and status updates"),
                    ("/promote", "Promote a member to the next rank"),
                    ("/demote", "Demote a member to the previous rank"),
                    ("/draxon-backup", "Create a backup of the server configuration"),
                    ("/draxon-restore", "Restore server configuration from a backup file")
                ]
                
                for cmd_name, cmd_desc in chairman_commands:
                    embed.add_field(
                        name=cmd_name,
                        value=cmd_desc,
                        inline=False
                    )

        embed.set_footer(text=f"DraXon AI v{APP_VERSION}")
        
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