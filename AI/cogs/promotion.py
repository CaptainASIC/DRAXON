import discord
from discord import app_commands
from discord.ext import commands
import logging
import random
from typing import Optional, List
from lib.constants import (
    ROLE_HIERARCHY, 
    DraXon_ROLES, 
    PROMOTION_MESSAGES, 
    PROMOTION_TIMEOUT,
    MAX_PROMOTION_OPTIONS
)

logger = logging.getLogger('DraXon_AI')

class PromotionModal(discord.ui.Modal, title='Member Promotion'):
    def __init__(self, member: discord.Member, new_rank: str):
        super().__init__()
        self.member = member
        self.new_rank = new_rank
        
        self.reason = discord.ui.TextInput(
            label='Promotion Reason',
            placeholder='Enter the reason for promotion...',
            required=True,
            min_length=10,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            promotion_cog = interaction.client.get_cog('PromotionCog')
            if not promotion_cog:
                await interaction.followup.send(PROMOTION_MESSAGES['system_error'], ephemeral=True)
                return

            await promotion_cog.process_promotion(
                interaction,
                self.member,
                self.new_rank,
                str(self.reason)
            )

        except Exception as e:
            logger.error(f"Error in promotion modal: {e}")
            await interaction.followup.send(PROMOTION_MESSAGES['error'], ephemeral=True)

class DemotionModal(discord.ui.Modal, title='Member Demotion'):
    def __init__(self, member: discord.Member, new_rank: str):
        super().__init__()
        self.member = member
        self.new_rank = new_rank
        
        self.reason = discord.ui.TextInput(
            label='Demotion Reason',
            placeholder='Enter the reason for demotion...',
            required=True,
            min_length=10,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            promotion_cog = interaction.client.get_cog('PromotionCog')
            if not promotion_cog:
                await interaction.followup.send(PROMOTION_MESSAGES['system_error'], ephemeral=True)
                return

            await promotion_cog.process_demotion(
                interaction,
                self.member,
                self.new_rank,
                str(self.reason)
            )

        except Exception as e:
            logger.error(f"Error in demotion modal: {e}")
            await interaction.followup.send(PROMOTION_MESSAGES['error'], ephemeral=True)

class MemberSelect(discord.ui.Select):
    def __init__(self, members: List[discord.Member]):
        options = [
            discord.SelectOption(
                label=member.display_name,
                value=str(member.id),
                description=f"Current Role: {next((r.name for r in member.roles if r.name in ROLE_HIERARCHY), 'None')}"
            ) for member in members
        ]
        
        super().__init__(
            placeholder="Select member...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.handle_member_select(interaction, self.values[0])

class RoleSelect(discord.ui.Select):
    def __init__(self, available_roles: List[str] = None):
        options = [
            discord.SelectOption(
                label=role,
                value=role,
                description=f"Change to {role}"
            ) for role in (available_roles or [])
        ] or [
            discord.SelectOption(
                label="Select member first",
                value="none",
                description="Please select a member before choosing a role"
            )
        ]
        
        super().__init__(
            placeholder="Select new role (select member first)...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=True
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(PROMOTION_MESSAGES['member_first'], ephemeral=True)
            return
            
        view = self.view
        await view.handle_role_select(interaction, self.values[0])

class PromotionView(discord.ui.View):
    def __init__(self, cog, members: List[discord.Member]):
        super().__init__(timeout=PROMOTION_TIMEOUT)
        self.cog = cog
        self.member_select = MemberSelect(members)
        self.role_select = RoleSelect([])
        self.selected_member = None
        
        self.add_item(self.member_select)
        self.add_item(self.role_select)

    async def handle_member_select(self, interaction: discord.Interaction, member_id: str):
        """Handle member selection"""
        try:
            member = interaction.guild.get_member(int(member_id))
            if not member:
                await interaction.response.send_message(PROMOTION_MESSAGES['member_not_found'], ephemeral=True)
                return

            # Get available roles for promotion
            available_roles = self.cog.get_available_roles(member)
            if not available_roles:
                await interaction.response.send_message(PROMOTION_MESSAGES['no_promotion'], ephemeral=True)
                return

            # Update role select with available roles
            self.selected_member = member
            
            # Create new RoleSelect with the available roles
            self.remove_item(self.role_select)
            self.role_select = RoleSelect(available_roles)
            self.role_select.disabled = False
            self.add_item(self.role_select)

            await interaction.response.edit_message(view=self)

        except Exception as e:
            logger.error(f"Error in member selection: {e}")
            await interaction.response.send_message(PROMOTION_MESSAGES['error'], ephemeral=True)

    async def handle_role_select(self, interaction: discord.Interaction, role_name: str):
        """Handle role selection"""
        try:
            if not self.selected_member:
                await interaction.response.send_message(PROMOTION_MESSAGES['member_first'], ephemeral=True)
                return

            # Show promotion modal
            modal = PromotionModal(self.selected_member, role_name)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error in role selection: {e}")
            await interaction.response.send_message(PROMOTION_MESSAGES['error'], ephemeral=True)

    async def on_timeout(self):
        """Disable all components on timeout"""
        for child in self.children:
            child.disabled = True

class DemotionView(discord.ui.View):
    def __init__(self, cog, members: List[discord.Member]):
        super().__init__(timeout=PROMOTION_TIMEOUT)
        self.cog = cog
        
        # Filter members to only those who can be demoted
        eligible_members = [
            member for member in members
            if any(role.name in ROLE_HIERARCHY[1:] for role in member.roles)  # Exclude lowest rank
        ]
        
        self.member_select = MemberSelect(eligible_members)
        self.role_select = RoleSelect([])
        self.selected_member = None
        
        self.add_item(self.member_select)
        self.add_item(self.role_select)

    async def handle_member_select(self, interaction: discord.Interaction, member_id: str):
        """Handle member selection"""
        try:
            member = interaction.guild.get_member(int(member_id))
            if not member:
                await interaction.response.send_message(PROMOTION_MESSAGES['member_not_found'], ephemeral=True)
                return

            # Get available roles for demotion
            available_roles = self.cog.get_available_demotion_roles(member)
            if not available_roles:
                await interaction.response.send_message(PROMOTION_MESSAGES['no_demotion'], ephemeral=True)
                return

            # Update role select with available roles
            self.selected_member = member
            
            # Create new RoleSelect with the available roles
            self.remove_item(self.role_select)
            self.role_select = RoleSelect(available_roles)
            self.role_select.disabled = False
            self.role_select.placeholder = "Select new (lower) rank..."
            self.add_item(self.role_select)

            await interaction.response.edit_message(view=self)

        except Exception as e:
            logger.error(f"Error in member selection for demotion: {e}")
            await interaction.response.send_message(PROMOTION_MESSAGES['error'], ephemeral=True)

    async def handle_role_select(self, interaction: discord.Interaction, role_name: str):
        """Handle role selection"""
        try:
            if not self.selected_member:
                await interaction.response.send_message(PROMOTION_MESSAGES['member_first'], ephemeral=True)
                return

            # Show demotion modal
            modal = DemotionModal(self.selected_member, role_name)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error in role selection for demotion: {e}")
            await interaction.response.send_message(PROMOTION_MESSAGES['error'], ephemeral=True)

    async def on_timeout(self):
        """Disable all components on timeout"""
        for child in self.children:
            child.disabled = True

class PromotionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_available_roles(self, member: discord.Member) -> List[str]:
        """Get list of roles available for promotion"""
        current_rank = None
        for role in member.roles:
            if role.name in ROLE_HIERARCHY:
                current_rank = role.name
                break

        if not current_rank:
            return ROLE_HIERARCHY[:MAX_PROMOTION_OPTIONS]  # First available ranks if no current rank

        current_index = ROLE_HIERARCHY.index(current_rank)
        if current_index + 1 >= len(ROLE_HIERARCHY):
            return []  # No promotion possible
            
        return ROLE_HIERARCHY[current_index + 1:current_index + MAX_PROMOTION_OPTIONS]

    def get_available_demotion_roles(self, member: discord.Member) -> List[str]:
        """Get list of roles available for demotion"""
        current_rank = None
        for role in member.roles:
            if role.name in ROLE_HIERARCHY:
                current_rank = role.name
                break

        if not current_rank or current_rank == ROLE_HIERARCHY[0]:
            return []  # No demotion possible for lowest rank

        current_index = ROLE_HIERARCHY.index(current_rank)
        return ROLE_HIERARCHY[max(0, current_index - MAX_PROMOTION_OPTIONS):current_index]  # Get available lower ranks

    def format_promotion_announcement(self, member: discord.Member, new_rank: str, reason: str) -> str:
        """Format a professional promotion announcement"""
        announcements = [
            f"🎉 **DraXon Promotion Announcement** 🎉\n\n"
            f"@everyone\n\n"
            f"It is with great pleasure that we announce the promotion of {member.mention} "
            f"to the position of **{new_rank}**!\n\n"
            f"📋 **Promotion Details**\n"
            f"• Previous Role: {next((r.name for r in member.roles if r.name in ROLE_HIERARCHY), 'None')}\n"
            f"• New Role: {new_rank}\n"
            f"• Reason: {reason}\n\n"
            f"Please join us in congratulating {member.mention} on this well-deserved promotion! 🚀",

            f"🌟 **Promotion Announcement** 🌟\n\n"
            f"@everyone\n\n"
            f"We are delighted to announce that {member.mention} has been promoted to "
            f"the role of **{new_rank}**!\n\n"
            f"🎯 **Achievement Details**\n"
            f"• Advanced from: {next((r.name for r in member.roles if r.name in ROLE_HIERARCHY), 'None')}\n"
            f"• New Position: {new_rank}\n"
            f"• Reason: {reason}\n\n"
            f"Congratulations on this outstanding achievement! 🏆"
        ]
        
        return random.choice(announcements)

    def format_demotion_announcement(self, member: discord.Member, new_rank: str, reason: str) -> str:
        """Format a professional demotion announcement"""
        announcements = [
            f"📢 **DraXon Personnel Notice** 📢\n\n"
            f"@everyone\n\n"
            f"This notice serves to inform all members that {member.mention} has been reassigned to the position of **{new_rank}**.\n\n"
            f"📋 **Position Update**\n"
            f"• Previous Role: {next((r.name for r in member.roles if r.name in ROLE_HIERARCHY), 'None')}\n"
            f"• New Role: {new_rank}\n"
            f"• Reason: {reason}\n\n"
            f"This change is effective immediately. 📝",

            f"⚠️ **DraXon Rank Adjustment** ⚠️\n\n"
            f"@everyone\n\n"
            f"Please be advised that {member.mention}'s position has been adjusted to **{new_rank}**.\n\n"
            f"📊 **Status Update**\n"
            f"• Previous Position: {next((r.name for r in member.roles if r.name in ROLE_HIERARCHY), 'None')}\n"
            f"• Updated Position: {new_rank}\n"
            f"• Reason: {reason}\n\n"
            f"This change takes effect immediately. 📌"
        ]
        
        return random.choice(announcements)

    async def process_promotion(self, interaction: discord.Interaction, member: discord.Member, 
                              new_rank: str, reason: str):
        """Process the actual promotion"""
        try:
            # Verify promotion channel is configured
            if not hasattr(self.bot, 'promotion_channel_id') or not self.bot.promotion_channel_id:
                await interaction.followup.send(PROMOTION_MESSAGES['channel_config'], ephemeral=True)
                return

            # Get the roles
            new_role = discord.utils.get(interaction.guild.roles, name=new_rank)
            if not new_role:
                await interaction.followup.send(PROMOTION_MESSAGES['role_not_found'], ephemeral=True)
                return

            # Remove current rank role
            current_rank = next((r for r in member.roles if r.name in ROLE_HIERARCHY), None)
            if current_rank:
                await member.remove_roles(current_rank)

            # Add new role
            await member.add_roles(new_role)
            
            # Send promotion announcement
            announcement = self.format_promotion_announcement(member, new_rank, reason)
            channel = self.bot.get_channel(self.bot.promotion_channel_id)
            
            if channel:
                await channel.send(announcement)
                
            await interaction.followup.send(
                PROMOTION_MESSAGES['success'].format(member=member.mention, rank=new_rank),
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error processing promotion: {e}")
            await interaction.followup.send(PROMOTION_MESSAGES['error'], ephemeral=True)

    async def process_demotion(self, interaction: discord.Interaction, member: discord.Member, 
                                new_rank: str, reason: str):
        """Process the actual demotion"""
        try:
            # Verify promotion channel is configured
            if not hasattr(self.bot, 'promotion_channel_id') or not self.bot.promotion_channel_id:
                await interaction.followup.send(PROMOTION_MESSAGES['channel_config'], ephemeral=True)
                return

            # Get the roles
            new_role = discord.utils.get(interaction.guild.roles, name=new_rank)
            if not new_role:
                await interaction.followup.send(PROMOTION_MESSAGES['role_not_found'], ephemeral=True)
                return

            # Remove current rank role
            current_rank = next((r for r in member.roles if r.name in ROLE_HIERARCHY), None)
            if current_rank:
                await member.remove_roles(current_rank)

            # Add new role
            await member.add_roles(new_role)
            
            # Send demotion announcement
            announcement = self.format_demotion_announcement(member, new_rank, reason)
            channel = self.bot.get_channel(self.bot.promotion_channel_id)
            
            if channel:
                await channel.send(announcement)
                
            await interaction.followup.send(
                PROMOTION_MESSAGES['demotion_success'].format(member=member.mention, rank=new_rank),
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error processing demotion: {e}")
            await interaction.followup.send(PROMOTION_MESSAGES['error'], ephemeral=True)

    @app_commands.command(name="promote", description="Promote a member to a higher rank")
    @app_commands.checks.has_any_role("Chairman", "Director")
    async def promote(self, interaction: discord.Interaction):
        """Promote command with modal interface"""
        try:
            # Get eligible members (exclude bots and highest ranked)
            eligible_members = [
                member for member in interaction.guild.members
                if not member.bot and
                not any(role.name == ROLE_HIERARCHY[-1] for role in member.roles)
            ]

            if not eligible_members:
                await interaction.response.send_message(PROMOTION_MESSAGES['no_members'], ephemeral=True)
                return

            # Create and send view with member selection
            view = PromotionView(self, eligible_members)
            await interaction.response.send_message(
                "Please select a member to promote:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in promote command: {e}")
            await interaction.response.send_message(PROMOTION_MESSAGES['error'], ephemeral=True)

    @app_commands.command(name="demote", description="Demote a member to a lower rank")
    @app_commands.checks.has_any_role("Chairman", "Director")
    async def demote(self, interaction: discord.Interaction):
        """Demote command with modal interface"""
        try:
            # Get eligible members (exclude bots and lowest ranked)
            eligible_members = [
                member for member in interaction.guild.members
                if not member.bot and
                any(role.name in ROLE_HIERARCHY[1:] for role in member.roles)
            ]

            if not eligible_members:
                await interaction.response.send_message(PROMOTION_MESSAGES['no_members_demotion'], ephemeral=True)
                return

            # Create and send view with member selection
            view = DemotionView(self, eligible_members)
            await interaction.response.send_message(
                "Please select a member to demote:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in demote command: {e}")
            await interaction.response.send_message(PROMOTION_MESSAGES['error'], ephemeral=True)

async def setup(bot):
    await bot.add_cog(PromotionCog(bot))