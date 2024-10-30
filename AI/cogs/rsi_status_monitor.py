import discord
from discord.ext import commands
import logging
import requests
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, Optional
from lib.constants import STATUS_EMOJIS

logger = logging.getLogger('DraXon_AI')

class RSIStatusMonitorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session
        self.max_retries = 3
        self.timeout = 10
        self.status_url = "https://status.robertsspaceindustries.com/"
        self.system_statuses = {
            'platform': 'operational',
            'persistent-universe': 'operational',
            'electronic-access': 'operational'
        }

    async def make_request(self) -> Optional[requests.Response]:
        """Make HTTP request with retries and timeout"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(self.status_url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All retry attempts failed for {self.status_url}")
                    return None
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        return None

    def get_status_emoji(self, status: str) -> str:
        """Get emoji for status"""
        return STATUS_EMOJIS.get(status, '❓')

    async def check_status(self) -> Dict[str, str]:
        """Check RSI status page and return current statuses"""
        logger.info("Checking RSI server status...")
        try:
            response = await self.make_request()
            if not response:
                return self.system_statuses

            soup = BeautifulSoup(response.text, 'html.parser')
            components = soup.find_all('div', class_='component')
            
            status_changed = False
            for component in components:
                name = component.text.strip().split('\n')[0].lower()
                status_span = component.find('span', class_='component-status')
                if status_span:
                    status = status_span.get('data-status', 'unknown')
                    
                    if 'platform' in name:
                        if self.system_statuses['platform'] != status:
                            status_changed = True
                        self.system_statuses['platform'] = status
                    elif 'persistent universe' in name:
                        if self.system_statuses['persistent-universe'] != status:
                            status_changed = True
                        self.system_statuses['persistent-universe'] = status
                    elif 'arena commander' in name:
                        if self.system_statuses['electronic-access'] != status:
                            status_changed = True
                        self.system_statuses['electronic-access'] = status

            if status_changed:
                logger.info(f"Status changed - new statuses: {self.system_statuses}")
            else:
                logger.info("No status changes detected")

            return self.system_statuses

        except Exception as e:
            logger.error(f"Error checking server status: {e}")
            return self.system_statuses

async def setup(bot):
    await bot.add_cog(RSIStatusMonitorCog(bot))