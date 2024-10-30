from discord.ext import commands, tasks
import logging
from lib.constants import CHANNELS_CONFIG

logger = logging.getLogger('DraXon_AI')

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task_started = False
        self.update_server_status.start()

    def cog_unload(self):
        self.update_server_status.cancel()

    @tasks.loop(minutes=30)
    async def update_server_status(self):
        """Check RSI status page every 30 minutes"""
        if not self.bot.is_ready():
            return

        try:
            # Get status monitor cog
            status_monitor = self.bot.get_cog('RSIStatusMonitorCog')
            if not status_monitor:
                logger.error("RSIStatusMonitorCog not found")
                return

            logger.info("Starting server status check...")
            new_statuses = await status_monitor.check_status()
            if not new_statuses:
                logger.error("Failed to get status update")
                return
                
            # Update channel names if needed
            await self._update_status_channels(new_statuses)

        except Exception as e:
            logger.error(f"Error in update_server_status: {e}")

    async def _update_status_channels(self, statuses):
        """Update status channels"""
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

                for config in CHANNELS_CONFIG:
                    if config["count_type"] != "status":
                        continue

                    base_name = config["name"].lower()
                    channel = next((ch for ch in category.voice_channels 
                                  if ch.name.lower().startswith(base_name)), None)

                    if channel:
                        system_name = config["name"].replace("-status", "")
                        status = statuses.get(system_name, 'operational')
                        new_name = channels_cog.get_channel_name(config, status=status)

                        if channel.name != new_name:
                            try:
                                await channel.edit(name=new_name)
                                logger.info(f"Updated status channel to: {new_name}")
                            except Exception as e:
                                logger.error(f"Failed to update status channel: {e}")

            except Exception as e:
                logger.error(f"Error updating status channels in {guild.name}: {e}")

    @update_server_status.before_loop
    async def before_status_update(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(StatusCog(bot))