import discord
from discord.ext import commands, tasks
import logging
from lib.constants import STATUS_EMOJIS
from lib.rsi_incidents import RSIIncidentMonitor
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger('DraXon_AI')

class IncidentsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.incident_monitor = RSIIncidentMonitor(bot.session)
        self.check_incidents.start()

    def cog_unload(self):
        self.check_incidents.cancel()

    def format_timestamp(self, timestamp_str):
        """Format timestamp to a cleaner discord format"""
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
            return discord.utils.format_dt(timestamp, style='f')  # Full date time format
        except Exception as e:
            logger.error(f"Error formatting timestamp: {e}")
            return timestamp_str

    def clean_html_content(self, html_content):
        """Clean and format HTML content"""
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Format updates sections
            formatted_text = []
            current_section = []
            
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if not text:
                    continue
                    
                # Check if this is a date header
                if text.startswith('[20'):  # Date headers like [2024-10-26 Updates]
                    if current_section:
                        formatted_text.append('\n'.join(current_section))
                        current_section = []
                    formatted_text.append(f"\n**{text}**")
                else:
                    # Clean up UTC timestamps
                    if ' UTC - ' in text:
                        time, message = text.split(' UTC - ', 1)
                        text = f"`{time} UTC` - {message}"
                    current_section.append(text)
            
            if current_section:
                formatted_text.append('\n'.join(current_section))
            
            return '\n'.join(formatted_text)
            
        except Exception as e:
            logger.error(f"Error cleaning HTML content: {e}")
            return html_content

    @tasks.loop(hours=1)
    async def check_incidents(self):
        """Check RSS feed for new incidents every hour"""
        if not self.bot.is_ready() or not self.bot.incidents_channel_id:
            return
            
        try:
            incident = await self.incident_monitor.check_incidents()
            if incident:
                # Create embed
                embed = discord.Embed(
                    title=incident['title'],
                    color=discord.Color.orange() if 'partial' in incident['title'].lower() 
                           else discord.Color.red() if 'major' in incident['title'].lower()
                           else discord.Color.green() if 'resolved' in incident['title'].lower()
                           else discord.Color.blue()
                )
                
                # Clean and add description
                cleaned_description = self.clean_html_content(incident['description'])
                embed.description = cleaned_description
                
                # Add affected systems
                if incident.get('tags'):
                    affected_systems = [tag['term'] for tag in incident['tags']]
                    embed.add_field(
                        name="🎯 Affected Systems",
                        value='\n'.join(f"- {system}" for system in affected_systems),
                        inline=False
                    )
                
                # Add timestamp
                embed.timestamp = incident['timestamp']
                embed.set_footer(text="RSI Status Update")
                
                # Send to channel
                channel = self.bot.get_channel(self.bot.incidents_channel_id)
                if channel:
                    await channel.send(embed=embed)
                    logger.info("Incident notification sent")
                
        except Exception as e:
            logger.error(f"Error checking incidents: {e}")

async def setup(bot):
    await bot.add_cog(IncidentsCog(bot))