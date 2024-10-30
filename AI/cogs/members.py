import discord
from discord.ext import commands, tasks
import logging
from lib.constants import CHANNELS_CONFIG

logger = logging.getLogger('DraXon_AI')

class MembersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task_started = False
        self.update_member_counts.start()

    def cog_unload(self):
        self.update_member_counts.cancel()

    @tasks.loop(minutes=5)
    async def update_member_counts(self):
        """Update member count channels every 5 minutes"""
        if not self.bot.is_ready():
            return
            
        logger.info("Starting member count update cycle...")
        channels_cog = self.bot.get_cog('ChannelsCog')
        if not channels_cog:
            logger.error("ChannelsCog not found")
            return
        
        for guild in self.bot.guilds:
            try:
                category = await channels_cog.get_category(guild)
                if not category:
                    logger.warning(f"No DraXon AI category found in {guild.name}")
                    continue

                logger.info(f"Updating counts for guild: {guild.name}")

                for config in CHANNELS_CONFIG:
                    if config["count_type"] not in ["members", "bots"]:
                        continue

                    display_start = config["display"].split(':')[0]
                    logger.info(f"Looking for channel starting with: {display_start}")
                    
                    matching_channels = [ch for ch in category.voice_channels 
                                      if ch.name.startswith(display_start)]
                    
                    if not matching_channels:
                        continue
                        
                    channel = matching_channels[0]
                    logger.info(f"Found matching channel: {channel.name}")

                    if config["count_type"] == "members":
                        count = len([m for m in guild.members if not m.bot])
                        logger.info(f"Calculated {count} human members")
                    else:  # bots
                        bot_role = discord.utils.get(guild.roles, name="Bots")
                        count = len(bot_role.members) if bot_role else 0
                        logger.info(f"Calculated {count} bot members")

                    new_name = channels_cog.get_channel_name(config, count=count)
                    logger.info(f"Current channel name: {channel.name}")
                    logger.info(f"New channel name would be: {new_name}")

                    if channel.name != new_name:
                        try:
                            await channel.edit(name=new_name)
                            logger.info(f"Successfully updated channel name to: {new_name}")
                        except Exception as e:
                            logger.error(f"Failed to update channel name: {e}")

            except Exception as e:
                logger.error(f"Error updating member counts in {guild.name}: {e}")

        logger.info("Member count update cycle completed")

    @update_member_counts.before_loop
    async def before_member_update(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(MembersCog(bot))