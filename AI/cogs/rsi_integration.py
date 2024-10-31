import discord
from discord import app_commands
from discord.ext import commands
import logging
import aiohttp
import json
import io
import os
import datetime
from typing import Dict, List, Optional
from lib.constants import (
    RSI_API_BASE_URL,
    RSI_API_VERSION,
    RSI_API_MODE,
    RSI_ORGANIZATION_SID,
    COMPARE_STATUS,
    RSI_MEMBERS_PER_PAGE,
    DB_DIR,
    RSI_DB_PATH,
    API_MAINTENANCE_START,
    API_MAINTENANCE_DURATION
)
from lib.rsi_db import RSIDatabase

logger = logging.getLogger('DraXon_AI')

class RSIIntegrationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('RSI_API_KEY')
        # Initialize database
        DB_DIR.mkdir(exist_ok=True)
        self.db = RSIDatabase(RSI_DB_PATH)
        if not self.api_key:
            logger.error("RSI API key not found in environment variables")

    async def fetch_api_data(self, endpoint: str, params: Dict = None) -> Dict:
        """Generic method to fetch data from RSI API"""
        url = f"{RSI_API_BASE_URL}/{self.api_key}/{RSI_API_VERSION}/{RSI_API_MODE}/{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"API request failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching API data: {e}")
            return None

    async def get_user_info(self, handle: str) -> Dict:
        """Fetch user information from RSI API"""
        return await self.fetch_api_data(f"user/{handle}")

    async def get_org_members(self) -> List[Dict]:
        """Fetch all organization members from RSI API"""
        members = []
        page = 1
        try:
            while True:
                data = await self.fetch_api_data(f"organization_members/{RSI_ORGANIZATION_SID}", 
                                               params={"page": page})
                if not data or not data.get('data'):
                    break
                members.extend(data['data'])
                if len(data['data']) < RSI_MEMBERS_PER_PAGE:
                    break
                page += 1
            return members
        except Exception as e:
            logger.error(f"Error fetching org members: {e}")
            return []

    async def create_member_table(self, members: List[Dict], include_roles: bool = True) -> str:
        """Create a formatted table of members"""
        table = "Discord ID | Discord Name | RSI Display Name | RSI Handle | Stars | Status | Rank"
        if include_roles:
            table += " | Roles"
        table += "\n" + "-" * 140 + "\n"

        # Sort by stars (descending)
        sorted_members = sorted(members, key=lambda x: x.get('stars', 0), reverse=True)

        for member in sorted_members:
            # Try to get Discord info from database
            discord_info = self.db.search_members({"handle": member['handle']})
            discord_member = None
            
            if discord_info:
                member_data = discord_info[0]
                for guild in self.bot.guilds:
                    discord_member = guild.get_member(int(member_data.get('discord_id')))
                    if discord_member:
                        break

            discord_id = discord_member.id if discord_member else "N/A"
            discord_name = discord_member.name if discord_member else "N/A"
            roles_str = ", ".join(member.get('roles', [])) if include_roles else ""
            org_status = member_data.get('org_status', 'Unknown') if discord_info else 'Unknown'
            
            row = (f"{discord_id} | {discord_name} | {member['display']} | "
                  f"{member['handle']} | {member.get('stars', 0)} | {org_status} | "
                  f"{member.get('rank', 'Unknown')}")
            if include_roles:
                row += f" | {roles_str}"
            table += row + "\n"

        return table

    async def create_comparison_table(self, discord_members: List[discord.Member], 
                                    org_members: List[Dict]) -> str:
        """Create comparison table between Discord and Org members"""
        table = ("Status | Discord ID | Discord Name | RSI Handle | RSI Display | Stars | "
                "Org Status | Last Updated\n")
        table += "-" * 140 + "\n"

        org_by_handle = {m['handle']: m for m in org_members}
        
        for member in discord_members:
            if member.bot:
                continue
                
            # Get member data from database
            member_data = self.db.get_member_by_discord_id(str(member.id))
            
            if member_data:
                handle = member_data.get('handle')
                org_member = org_by_handle.get(handle)
                
                status = COMPARE_STATUS['match'] if org_member else COMPARE_STATUS['missing']
                display = org_member['display'] if org_member else member_data.get('display', 'N/A')
                stars = str(org_member.get('stars', 'N/A')) if org_member else 'N/A'
                org_status = member_data.get('org_status', 'N/A')
                last_updated = member_data.get('last_updated', 'Never')[:16].replace('T', ' ')
            else:
                status = COMPARE_STATUS['missing']
                handle = 'N/A'
                display = 'N/A'
                stars = 'N/A'
                org_status = 'N/A'
                last_updated = 'Never'
            
            table += (f"{status} | {member.id} | {member.name} | {handle} | {display} | "
                     f"{stars} | {org_status} | {last_updated}\n")

        return table

    @app_commands.command(name="draxon-link", description="Link your RSI account")
    async def link_account(self, interaction: discord.Interaction):
        """Command to link RSI account"""
        modal = LinkAccountModal()
        modal.cog = self
        await interaction.response.send_modal(modal)

    @app_commands.command(name="draxon-org", description="Display organization member list")
    @app_commands.checks.has_role("Chairman")
    async def org_members(self, interaction: discord.Interaction):
        """Command to display organization members"""
        await interaction.response.defer()

        try:
            members = await self.get_org_members()
            if not members:
                await interaction.followup.send("❌ Failed to fetch organization members.")
                return

            table = await self.create_member_table(members)
            
            file = discord.File(
                io.StringIO(table),
                filename=f'draxon_members_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            )

            await interaction.followup.send(
                "Organization Members List (attached as file)",
                file=file
            )

        except Exception as e:
            logger.error(f"Error in org_members command: {e}")
            await interaction.followup.send("❌ An error occurred while fetching member data.")

    @app_commands.command(name="draxon-compare", description="Compare Discord and Org members")
    @app_commands.checks.has_role("Chairman")
    async def compare_members(self, interaction: discord.Interaction):
        """Command to compare Discord and Org members"""
        await interaction.response.defer()

        try:
            org_members = await self.get_org_members()
            if not members:
                await interaction.followup.send("❌ Failed to fetch organization members.")
                return

            guild_members = interaction.guild.members
            table = await self.create_comparison_table(guild_members, org_members)
            
            file = discord.File(
                io.StringIO(table),
                filename=f'draxon_comparison_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            )

            await interaction.followup.send(
                "Member Comparison (attached as file)",
                file=file
            )

        except Exception as e:
            logger.error(f"Error in compare_members command: {e}")
            await interaction.followup.send("❌ An error occurred while comparing members.")

class LinkAccountModal(discord.ui.Modal, title='Link RSI Account'):
    def __init__(self):
        super().__init__()
        self.handle = discord.ui.TextInput(
            label='RSI Handle',
            placeholder='Enter your RSI Handle (case sensitive)...',
            required=True,
            max_length=50
        )
        self.add_item(self.handle)
        self.cog = None

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            logger.info(f"Searching for RSI Handle: {self.handle.value}")
            
            response = await self.cog.get_user_info(self.handle.value)
            logger.info(f"Full API Response: {json.dumps(response, indent=2)}")

            # Check for API unavailability response
            if response and not response.get('success') and response.get('message') == "Can't process the request." and response.get('data') is None:
                await interaction.followup.send(
                    "⚠️ **RSI API is Currently Unavailable**\n\n"
                    "The RSI API is experiencing downtime. This is a known issue that occurs daily "
                    f"from {API_MAINTENANCE_START} UTC for approximately {API_MAINTENANCE_DURATION} hours.\n\n"
                    "Please try again later when the API service has been restored.",
                    ephemeral=True
                )
                return

            if not response or not response.get('success'):
                await interaction.followup.send(
                    "❌ Invalid RSI Handle. Please check your handle and try again.",
                    ephemeral=True
                )
                return

            try:
                data = response.get('data', {})
                profile = data.get('profile', {})
                main_org = data.get('organization', {})
                affiliations = data.get('affiliation', [])

                if not profile:
                    await interaction.followup.send(
                        "❌ Could not retrieve profile information.",
                        ephemeral=True
                    )
                    return

                # Check DraXon membership
                is_main_org = main_org.get('sid') == RSI_ORGANIZATION_SID
                is_affiliate = any(org.get('sid') == RSI_ORGANIZATION_SID for org in affiliations)

                if not is_main_org and not is_affiliate:
                    await interaction.followup.send(
                        "⚠️ Your RSI Handle was found, but you don't appear to be a member of our organization. " +
                        "Please join our organization first and try again.",
                        ephemeral=True
                    )
                    return

                # Get DraXon org data
                draxon_org = main_org if is_main_org else next(
                    org for org in affiliations if org.get('sid') == RSI_ORGANIZATION_SID
                )

                # Prepare data for storage
                rsi_data = {
                    'discord_id': str(interaction.user.id),
                    'sid': profile.get('id', '').replace('#', ''),
                    'handle': profile.get('handle', self.handle.value),
                    'display': profile.get('display', self.handle.value),
                    'verified': True,
                    'enlisted': profile.get('enlisted', ''),
                    'org_sid': draxon_org.get('sid', ''),
                    'org_name': draxon_org.get('name', ''),
                    'org_rank': draxon_org.get('rank', ''),
                    'org_stars': draxon_org.get('stars', 0),
                    'org_status': 'Main' if is_main_org else 'Affiliate',
                    'last_updated': datetime.datetime.utcnow().isoformat(),
                    'raw_profile': profile,
                    'raw_org': draxon_org
                }

                # Store in database
                success = await self.cog.db.store_member(str(interaction.user.id), rsi_data)
                
                if success:
                    response_msg = [
                        "✅ RSI Account Successfully Linked!",
                        "",
                        "**Account Information:**",
                        f"🔹 Handle: {rsi_data['handle']}",
                        f"🔹 Display Name: {rsi_data['display']}",
                        f"🔹 Citizen ID: {rsi_data['sid']}",
                        f"🔹 Enlisted: {rsi_data['enlisted'][:10]}",
                        "",
                        "**Organization Status:**",
                        f"🔹 Organization: {rsi_data['org_name']}",
                        f"🔹 Status: {rsi_data['org_status']}",
                        f"🔹 Rank: {rsi_data['org_rank']}",
                        f"🔹 Stars: {'⭐' * rsi_data['org_stars']}"
                    ]

                    await interaction.followup.send(
                        "\n".join(response_msg),
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ Failed to store RSI account information.",
                        ephemeral=True
                    )

            except Exception as e:
                logger.error(f"Error processing API response: {str(e)}")
                await interaction.followup.send(
                    "❌ Error processing RSI account information. Please try again.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error linking account: {e}")
            await interaction.followup.send(
                "❌ An error occurred while linking your account.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(RSIIntegrationCog(bot))