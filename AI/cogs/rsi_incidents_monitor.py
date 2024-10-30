import discord
from discord.ext import commands, tasks
import logging
import feedparser
import requests
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from lib.constants import STATUS_EMOJIS

logger = logging.getLogger('DraXon_AI')

class RSIIncidentMonitorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session
        self.max_retries = 3
        self.timeout = 10
        self.feed_url = "https://status.robertsspaceindustries.com/index.xml"
        self.last_incident_guid = None
        self.check_incidents_task.start()

    def cog_unload(self):
        self.check_incidents_task.cancel()

    async def make_request(self) -> Optional[requests.Response]:
        """Make HTTP request with retries and timeout"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(self.feed_url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All retry attempts failed for {self.feed_url}")
                    return None
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        return None

    async def check_incidents(self) -> Optional[Dict[str, Any]]:
        """Check RSS feed for new incidents"""
        logger.info("Checking RSS feed for new incidents...")
        try:
            response = await self.make_request()
            if not response:
                return None

            feed = feedparser.parse(response.text)
            if not feed.entries:
                return None
                
            latest = feed.entries[0]
            if self.last_incident_guid == latest.guid:
                return None

            self.last_incident_guid = latest.guid
            logger.info(f"New incident found: {latest.title}")

            # Clean HTML content
            description = self.clean_html_content(latest.description)

            return {
                'title': latest.title,
                'description': description,
                'url': latest.link,
                'timestamp': datetime.now(),
                'tags': getattr(latest, 'tags', []),
                'guid': latest.guid
            }

        except Exception as e:
            logger.error(f"Error checking incidents: {e}")
            return None

    def clean_html_content(self, html_content: str) -> str:
        """Clean and format HTML content"""
        try:
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

    def format_incident_embed(self, incident: Dict[str, Any]) -> discord.Embed:
        """Format incident data for Discord embed"""
        embed = discord.Embed(
            title=incident['title'],
            description=incident['description'],
            url=incident['url'],
            timestamp=incident['timestamp'],
            color=self.get_incident_color(incident['title'])
        )

        status = None
        components = []
        for tag in incident['tags']:
            if tag['term'] in STATUS_EMOJIS:
                status = tag['term']
            else:
                components.append(tag['term'])

        if status:
            embed.add_field(
                name="Status",
                value=f"{STATUS_EMOJIS[status]} {status.title()}",
                inline=False
            )

        if components:
            embed.add_field(
                name="🎯 Affected Systems",
                value="\n".join(f"- {component}" for component in components),
                inline=False
            )

        embed.set_footer(text="RSI Status Update")
        return embed

    def get_incident_color(self, title: str) -> discord.Color:
        """Determine embed color based on incident title"""
        title_lower = title.lower()
        if 'resolved' in title_lower:
            return discord.Color.green()
        elif 'major' in title_lower:
            return discord.Color.red()
        elif 'partial' in title_lower:
            return discord.Color.orange()
        else:
            return discord.Color.blue()

    @tasks.loop(hours=1)
    async def check_incidents_task(self):
        """Check RSS feed for new incidents every hour"""
        if not self.bot.is_ready() or not self.bot.incidents_channel_id:
            return
            
        try:
            incident = await self.check_incidents()
            if incident:
                embed = self.format_incident_embed(incident)
                
                channel = self.bot.get_channel(self.bot.incidents_channel_id)
                if channel:
                    await channel.send(embed=embed)
                    logger.info("Incident notification sent")
                
        except Exception as e:
            logger.error(f"Error checking incidents: {e}")

    @check_incidents_task.before_loop
    async def before_incidents_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RSIIncidentMonitorCog(bot))