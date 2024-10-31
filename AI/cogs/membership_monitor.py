import discord
from discord.ext import commands, tasks
import logging
import datetime
from typing import List, Dict, Set
from lib.constants import (
    ROLE_HIERARCHY,
    LEADERSHIP_MAX_RANK,
    DEFAULT_DEMOTION_RANK,
    UNAFFILIATED_RANK,
    UNLINKED_REMINDER_MESSAGE,
    DEMOTION_MESSAGES,
    DAILY_CHECK_TIME
)

logger = logging.getLogger('DraXon_AI')

class MembershipMonitorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_check = None
        self.daily_checks.start()

    def cog_unload(self):
        self.daily_checks.cancel()

    async def get_unlinked_members(self, guild: discord.Guild) -> List[discord.Member]:
        """Get list of members who haven't linked their RSI account"""
        rsi_cog = self.bot.get_cog('RSIIntegrationCog')
        if not rsi_cog:
            return []

        unlinked_members = []
        for member in guild.members:
            if member.bot:
                continue
            
            member_data = rsi_cog.db.get_member_by_discord_id(str(member.id))
            if not member_data:
                unlinked_members.append(member)

        return unlinked_members

    async def check_member_roles(self, guild: discord.Guild) -> List[Dict]:
        """Check and adjust member roles based on org status"""
        rsi_cog = self.bot.get_cog('RSIIntegrationCog')
        if not rsi_cog:
            logger.error("RSIIntegrationCog not found")
            return []

        demotion_log = []
        employee_role = discord.utils.get(guild.roles, name=DEFAULT_DEMOTION_RANK)
        screening_role = discord.utils.get(guild.roles, name=UNAFFILIATED_RANK)

        if not employee_role or not screening_role:
            logger.error("Required roles not found")
            return []

        try:
            # Get current org members
            org_members = await rsi_cog.get_org_members()
            if org_members is None:
                logger.error("Failed to fetch organization members")
                return []

            org_handles = {m['handle'].lower() for m in org_members}

            for member in guild.members:
                if member.bot:
                    continue

                try:
                    member_data = rsi_cog.db.get_member_by_discord_id(str(member.id))
                    current_roles = [role.name for role in member.roles]
                    current_rank = next((r for r in current_roles if r in ROLE_HIERARCHY), None)
                    
                    if not member_data:
                        continue  # Skip unlinked members
                        
                    # Check if member is in org
                    member_handle = member_data.get('handle', '').lower()
                    in_org = member_handle in org_handles

                    if not in_org:
                        # Member not in org at all - set to Screening
                        if current_rank != UNAFFILIATED_RANK:
                            # Remove all rank roles
                            for rank in ROLE_HIERARCHY:
                                rank_role = discord.utils.get(guild.roles, name=rank)
                                if rank_role and rank_role in member.roles:
                                    await member.remove_roles(rank_role)
                            
                            # Add Screening role
                            await member.add_roles(screening_role)
                            demotion_log.append({
                                'member': member,
                                'old_rank': current_rank or "None",
                                'new_rank': UNAFFILIATED_RANK,
                                'reason': DEMOTION_MESSAGES['not_in_org']
                            })
                        continue

                    # Get member's org status
                    is_affiliate = member_data.get('org_status') == 'Affiliate'
                    
                    # Check if affiliate needs demotion
                    if is_affiliate and current_rank:
                        max_allowed_index = ROLE_HIERARCHY.index(LEADERSHIP_MAX_RANK)
                        current_index = ROLE_HIERARCHY.index(current_rank)
                        
                        if current_index > max_allowed_index:
                            # Remove current rank role
                            current_role = discord.utils.get(guild.roles, name=current_rank)
                            if current_role:
                                await member.remove_roles(current_role)
                            
                            # Add Employee role
                            await member.add_roles(employee_role)
                            
                            demotion_log.append({
                                'member': member,
                                'old_rank': current_rank,
                                'new_rank': DEFAULT_DEMOTION_RANK,
                                'reason': DEMOTION_MESSAGES['affiliate']
                            })

                            # Update database
                            member_data['org_rank'] = DEFAULT_DEMOTION_RANK
                            await rsi_cog.db.store_member(str(member.id), member_data)

                except Exception as e:
                    logger.error(f"Error processing member {member.name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in check_member_roles: {e}")

        return demotion_log

    async def send_demotion_notifications(self, guild: discord.Guild, demotions: List[Dict]):
        """Send notifications about demotions"""
        if not demotions or not hasattr(self.bot, 'demotion_channel_id'):
            return

        channel = self.bot.get_channel(self.bot.demotion_channel_id)
        if not channel:
            logger.error("Demotion channel not found")
            return

        for demotion in demotions:
            try:
                embed = discord.Embed(
                    title="🔄 Rank Update",
                    description=f"{demotion['member'].mention} has been updated to {demotion['new_rank']}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Previous Rank", value=demotion['old_rank'], inline=True)
                embed.add_field(name="New Rank", value=demotion['new_rank'], inline=True)
                embed.add_field(name="Reason", value=demotion['reason'], inline=False)
                embed.timestamp = datetime.datetime.utcnow()

                await channel.send(embed=embed)
                
                # Try to DM the member
                try:
                    await demotion['member'].send(
                        f"Your rank has been updated from {demotion['old_rank']} to "
                        f"{demotion['new_rank']} due to: {demotion['reason']}"
                    )
                except discord.Forbidden:
                    logger.warning(f"Could not send DM to {demotion['member'].name}")

            except Exception as e:
                logger.error(f"Error sending demotion notification: {e}")
                continue

    async def send_unlinked_reminders(self, guild: discord.Guild):
        """Send reminders to unlinked members and summary to notification channel"""
        if not hasattr(self.bot, 'reminder_channel_id'):
            logger.error("Reminder channel not configured")
            return

        try:
            unlinked_members = await self.get_unlinked_members(guild)
            if not unlinked_members:
                return

            # Send DMs to unlinked members
            for member in unlinked_members:
                try:
                    await member.send(UNLINKED_REMINDER_MESSAGE)
                except discord.Forbidden:
                    logger.warning(f"Could not send DM to {member.name}")
                except Exception as e:
                    logger.error(f"Error sending reminder to {member.name}: {e}")

            # Send summary to notification channel
            channel = self.bot.get_channel(self.bot.reminder_channel_id)
            if channel:
                embed = discord.Embed(
                    title="📊 Unlinked Members Report",
                    description="The following members have not yet linked their RSI accounts:",
                    color=discord.Color.blue()
                )
                
                members_list = "\n".join([f"• {member.mention}" for member in unlinked_members])
                if len(members_list) > 1024:  # Discord field value limit
                    members_list = members_list[:1021] + "..."
                
                embed.add_field(
                    name=f"Unlinked Members ({len(unlinked_members)})",
                    value=members_list or "No unlinked members",
                    inline=False
                )
                
                embed.timestamp = datetime.datetime.utcnow()
                await channel.send(embed=embed)
            else:
                logger.error("Reminder channel not found")

        except Exception as e:
            logger.error(f"Error in send_unlinked_reminders: {e}")

    @tasks.loop(hours=24)
    async def daily_checks(self):
        """Run daily checks and notifications"""
        logger.info("Starting daily membership checks")
        
        current_time = datetime.datetime.utcnow()
        if self.last_check:
            time_since_check = (current_time - self.last_check).total_seconds() / 3600
            if time_since_check < 23:  # Ensure at least 23 hours between checks
                return

        self.last_check = current_time
        
        for guild in self.bot.guilds:
            try:
                logger.info(f"Running checks for guild: {guild.name}")
                
                # Perform role checks and get demotion log
                demotions = await self.check_member_roles(guild)
                logger.info(f"Found {len(demotions)} role updates needed")
                
                # Send demotion notifications if any occurred
                await self.send_demotion_notifications(guild, demotions)
                
                # Send reminders to unlinked members
                await self.send_unlinked_reminders(guild)
                
                logger.info(f"Completed daily checks for guild: {guild.name}")
                
            except Exception as e:
                logger.error(f"Error in daily checks for guild {guild.name}: {e}")

    @daily_checks.before_loop
    async def before_daily_checks(self):
        await self.bot.wait_until_ready()
        
async def setup(bot):
    await bot.add_cog(MembershipMonitorCog(bot))