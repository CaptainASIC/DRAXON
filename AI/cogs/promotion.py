import discord
from discord import app_commands
from discord.ext import commands
import logging
import random
from typing import Optional
from lib.constants import DraXon_ROLES

logger = logging.getLogger('DraXon_AI')

class PromotionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ordered rank sequence
        self.rank_sequence = [
            'Applicant',
            'Employee',
            'Team Leader',
            'Manager',
            'Director',
            'Chairman'
        ]

    def get_next_rank(self, current_roles):
        """Determine the next rank in the sequence based on current roles"""
        current_rank = None
        for role_name in current_roles:
            if role_name in self.rank_sequence:
                current_rank = role_name
                break

        if not current_rank:
            return None

        current_index = self.rank_sequence.index(current_rank)
        if current_index + 1 < len(self.rank_sequence):
            return self.rank_sequence[current_index + 1]
        return None

    def get_previous_rank(self, current_roles):
        """Determine the previous rank in the sequence based on current roles"""
        current_rank = None
        for role_name in current_roles:
            if role_name in self.rank_sequence:
                current_rank = role_name
                break

        if not current_rank:
            return None

        current_index = self.rank_sequence.index(current_rank)
        if current_index > 0:
            return self.rank_sequence[current_index - 1]
        return None

    def format_promotion_announcement(self, member: discord.Member, new_rank: str) -> str:
        """Format a professional promotion announcement"""
        announcements = [
            f"🎉 **DraXon Promotion Announcement** 🎉\n\n"
            f"@everyone\n\n"
            f"It is with great pleasure that we announce the promotion of {member.mention} to the position of **{new_rank}**!\n\n"
            f"📋 **Promotion Details**\n"
            f"• Previous Role: {self.get_current_rank(member)}\n"
            f"• New Role: {new_rank}\n\n"
            f"Please join us in congratulating {member.mention} on this well-deserved promotion!\n"
            f"Your dedication and contributions to DraXon continue to drive our success. 🚀",

            f"🌟 **Promotion Announcement** 🌟\n\n"
            f"@everyone\n\n"
            f"We are delighted to announce that {member.mention} has been promoted to the role of **{new_rank}**!\n\n"
            f"🎯 **Achievement Details**\n"
            f"• Advanced from: {self.get_current_rank(member)}\n"
            f"• New Position: {new_rank}\n\n"
            f"Congratulations on this outstanding achievement! Your commitment to excellence exemplifies the DraXon spirit. 🏆",

            f"📢 **DraXon Personnel Update** 📢\n\n"
            f"@everyone\n\n"
            f"We are proud to announce the promotion of {member.mention} to **{new_rank}**!\n\n"
            f"📈 **Career Progression**\n"
            f"• Former Position: {self.get_current_rank(member)}\n"
            f"• New Role: {new_rank}\n\n"
            f"Join us in celebrating this milestone! Thank you for your continued dedication to DraXon's mission. ⭐"
        ]
        
        return random.choice(announcements)

    def format_demotion_announcement(self, member: discord.Member, new_rank: str) -> str:
        """Format a professional demotion announcement"""
        announcements = [
            f"📢 **DraXon Personnel Notice** 📢\n\n"
            f"@everyone\n\n"
            f"This notice serves to inform all members that {member.mention} has been reassigned to the position of **{new_rank}**.\n\n"
            f"📋 **Position Update**\n"
            f"• Previous Role: {self.get_current_rank(member)}\n"
            f"• New Role: {new_rank}\n\n"
            f"This change is effective immediately. 📝",

            f"⚠️ **DraXon Rank Adjustment** ⚠️\n\n"
            f"@everyone\n\n"
            f"Please be advised that {member.mention}'s position has been adjusted to **{new_rank}**.\n\n"
            f"📊 **Status Update**\n"
            f"• Previous Position: {self.get_current_rank(member)}\n"
            f"• Updated Position: {new_rank}\n\n"
            f"This change takes effect immediately. 📌",

            f"📋 **DraXon Administrative Update** 📋\n\n"
            f"@everyone\n\n"
            f"This notice confirms the reassignment of {member.mention} to the role of **{new_rank}**.\n\n"
            f"🔄 **Position Change**\n"
            f"• Former Role: {self.get_current_rank(member)}\n"
            f"• Current Role: {new_rank}\n\n"
            f"This administrative action is now in effect. ⚡"
        ]
        
        return random.choice(announcements)

    def get_current_rank(self, member: discord.Member) -> str:
        """Get the member's current rank"""
        for role_name in self.rank_sequence:
            if discord.utils.get(member.roles, name=role_name):
                return role_name
        return "Unranked"

    @app_commands.command(name="promote", description="Promote a member to the next rank")
    @app_commands.checks.has_any_role("Chairmen", "Directors")
    async def promote(self, interaction: discord.Interaction, member: discord.Member):
        """Promote a member to the next rank"""
        try:
            # Check if promotion channel is configured
            if not hasattr(self.bot, 'promotion_channel_id') or not self.bot.promotion_channel_id:
                await interaction.response.send_message(
                    "❌ Promotion channel not configured. Please use `/setup` first.",
                    ephemeral=True
                )
                return

            # Get current roles
            current_roles = [role.name for role in member.roles]
            next_rank = self.get_next_rank(current_roles)

            if not next_rank:
                await interaction.response.send_message(
                    f"❌ Cannot determine next rank for {member.mention}. They may be at the highest rank or have no valid rank.",
                    ephemeral=True
                )
                return

            # Get the roles
            next_role = discord.utils.get(interaction.guild.roles, name=next_rank)
            if not next_role:
                await interaction.response.send_message(
                    f"❌ Could not find the role {next_rank}",
                    ephemeral=True
                )
                return

            # Remove current rank role and add new one
            current_rank = self.get_current_rank(member)
            if current_rank != "Unranked":
                current_role = discord.utils.get(interaction.guild.roles, name=current_rank)
                if current_role:
                    await member.remove_roles(current_role)

            await member.add_roles(next_role)
            
            # Send promotion announcement
            announcement = self.format_promotion_announcement(member, next_rank)
            promotion_channel = self.bot.get_channel(self.bot.promotion_channel_id)
            
            if promotion_channel:
                await promotion_channel.send(announcement)
                
            await interaction.response.send_message(
                f"✅ Successfully promoted {member.mention} to {next_rank}!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to manage roles.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in promote command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the promotion.",
                ephemeral=True
            )

    @app_commands.command(name="demote", description="Demote a member to the previous rank")
    @app_commands.checks.has_any_role("Chairmen", "Directors")
    async def demote(self, interaction: discord.Interaction, member: discord.Member):
        """Demote a member to the previous rank"""
        try:
            # Check if promotion channel is configured
            if not hasattr(self.bot, 'promotion_channel_id') or not self.bot.promotion_channel_id:
                await interaction.response.send_message(
                    "❌ Announcement channel not configured. Please use `/setup` first.",
                    ephemeral=True
                )
                return

            # Get current roles
            current_roles = [role.name for role in member.roles]
            previous_rank = self.get_previous_rank(current_roles)

            if not previous_rank:
                await interaction.response.send_message(
                    f"❌ Cannot determine previous rank for {member.mention}. They may be at the lowest rank or have no valid rank.",
                    ephemeral=True
                )
                return

            # Get the roles
            previous_role = discord.utils.get(interaction.guild.roles, name=previous_rank)
            if not previous_role:
                await interaction.response.send_message(
                    f"❌ Could not find the role {previous_rank}",
                    ephemeral=True
                )
                return

            # Remove current rank role and add new one
            current_rank = self.get_current_rank(member)
            if current_rank != "Unranked":
                current_role = discord.utils.get(interaction.guild.roles, name=current_rank)
                if current_role:
                    await member.remove_roles(current_role)

            await member.add_roles(previous_role)
            
            # Send demotion announcement
            announcement = self.format_demotion_announcement(member, previous_rank)
            channel = self.bot.get_channel(self.bot.promotion_channel_id)
            
            if channel:
                await channel.send(announcement)
                
            await interaction.response.send_message(
                f"✅ Successfully demoted {member.mention} to {previous_rank}.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to manage roles.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in demote command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the demotion.",
                ephemeral=True
            )

async def setup(bot):
    """Safe setup function for promotion cog"""
    try:
        # Check if the cog is already loaded
        if not bot.get_cog('PromotionCog'):
            await bot.add_cog(PromotionCog(bot))
            logger.info('Promotion cog loaded successfully')
        else:
            logger.info('Promotion cog already loaded, skipping')
    except Exception as e:
        logger.error(f'Error loading promotion cog: {e}')
        raise