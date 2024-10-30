import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
import datetime
from typing import Dict, Any, Optional, List
import io
import asyncio

logger = logging.getLogger('DraXon_AI')

class BackupCog(commands.Cog):
    """Cog for handling server backup and restore operations"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("Backup cog initialized")

    async def backup_pins(self, channel: discord.TextChannel) -> List[Dict[str, Any]]:
        """Helper method to backup pins from a channel"""
        pins = []
        try:
            pins_iterator = await channel.pins()
            for message in pins_iterator:
                pins.append({
                    'content': message.content,
                    'author': str(message.author),
                    'created_at': message.created_at.isoformat(),
                    'attachments': [a.url for a in message.attachments]
                })
            logger.info(f"Successfully backed up {len(pins)} pins from {channel.name}")
        except Exception as e:
            logger.error(f"Error backing up pins from {channel.name}: {e}")
        return pins

    def serialize_overwrites(self, overwrites: Dict[Any, discord.PermissionOverwrite]) -> Dict[str, Dict[str, bool]]:
        """Serialize permission overwrites"""
        serialized = {}
        for target, overwrite in overwrites.items():
            # Store the target type and id
            if isinstance(target, discord.Role):
                key = f"role:{target.name}"
            else:  # Member
                key = f"member:{target.id}"
            
            # Convert overwrites to allow/deny pairs
            allow, deny = overwrite.pair()
            
            # Store as serializable dictionary
            serialized[key] = {
                'allow': allow.value,
                'deny': deny.value
            }
            
        return serialized

    def serialize_role(self, role: discord.Role) -> Dict[str, Any]:
        """Serialize a role's data"""
        return {
            'name': role.name,
            'permissions': role.permissions.value,
            'color': role.color.value,
            'hoist': role.hoist,
            'mentionable': role.mentionable,
            'position': role.position,
            'id': role.id
        }

    def serialize_channel(self, channel) -> Dict[str, Any]:
        """Serialize a channel's data"""
        base_data = {
            'name': channel.name,
            'type': str(channel.type),
            'position': channel.position,
            'overwrites': self.serialize_overwrites(channel.overwrites),
            'id': channel.id,
            'category_id': channel.category.id if channel.category else None
        }

        # Add type-specific data
        if isinstance(channel, discord.TextChannel):
            base_data.update({
                'topic': channel.topic,
                'nsfw': channel.nsfw,
                'slowmode_delay': channel.slowmode_delay,
                'default_auto_archive_duration': channel.default_auto_archive_duration,
            })
        elif isinstance(channel, discord.VoiceChannel):
            base_data.update({
                'bitrate': channel.bitrate,
                'user_limit': channel.user_limit,
            })
        elif isinstance(channel, discord.CategoryChannel):
            base_data.update({
                'is_category': True
            })

        return base_data

    def deserialize_overwrites(self, overwrites_data: Dict[str, Dict[str, int]], guild: discord.Guild) -> Dict[discord.Role, discord.PermissionOverwrite]:
        """Convert serialized overwrites back to Discord permission overwrites"""
        result = {}
        for key, data in overwrites_data.items():
            target_type, target_id = key.split(':', 1)
            
            if target_type == 'role':
                # Find role by name
                target = discord.utils.get(guild.roles, name=target_id)
            else:  # member
                # Find member by ID
                target = guild.get_member(int(target_id))
                
            if target:
                overwrite = discord.PermissionOverwrite()
                allow = discord.Permissions(data['allow'])
                deny = discord.Permissions(data['deny'])
                
                # Set each permission based on allow/deny values
                for perm, value in allow:
                    if value:
                        setattr(overwrite, perm, True)
                for perm, value in deny:
                    if value:
                        setattr(overwrite, perm, False)
                        
                result[target] = overwrite
                
        return result

    async def create_backup(self, guild: discord.Guild) -> Dict[str, Any]:
        """Create a comprehensive backup of the guild"""
        try:
            backup_data = {
                'name': guild.name,
                'icon_url': str(guild.icon.url) if guild.icon else None,
                'verification_level': str(guild.verification_level),
                'default_notifications': str(guild.default_notifications),
                'explicit_content_filter': str(guild.explicit_content_filter),
                'backup_date': datetime.datetime.utcnow().isoformat(),
                'roles': [],
                'categories': [],
                'channels': [],
                'bot_settings': {}
            }

            # Backup roles (excluding @everyone)
            for role in sorted(guild.roles[1:], key=lambda r: r.position):
                backup_data['roles'].append(self.serialize_role(role))

            # Backup categories first
            for category in guild.categories:
                backup_data['categories'].append(self.serialize_channel(category))

            # Backup channels (excluding categories)
            for channel in guild.channels:
                if not isinstance(channel, discord.CategoryChannel):
                    channel_data = self.serialize_channel(channel)
                    if isinstance(channel, discord.TextChannel):
                        # Backup pinned messages
                        channel_data['pins'] = await self.backup_pins(channel)

                    backup_data['channels'].append(channel_data)

            # Backup bot-specific settings
            if hasattr(self.bot, 'incidents_channel_id'):
                backup_data['bot_settings']['incidents_channel_id'] = self.bot.incidents_channel_id
            if hasattr(self.bot, 'promotion_channel_id'):
                backup_data['bot_settings']['promotion_channel_id'] = self.bot.promotion_channel_id

            return backup_data

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise

    async def restore_pins(self, channel: discord.TextChannel, pins_data: List[Dict[str, Any]]) -> List[str]:
        """Helper method to restore pins to a channel"""
        logs = []
        for pin in pins_data:
            try:
                message = await channel.send(
                    f"📌 Restored Pin from {pin['author']}\n{pin['content']}"
                )
                await message.pin()
                logs.append(f"✅ Restored pin in {channel.name}")
            except Exception as e:
                logs.append(f"⚠️ Error restoring pin in {channel.name}: {e}")
        return logs

    async def restore_channel(self, guild: discord.Guild, channel_data: Dict[str, Any], 
                            category_map: Dict[int, discord.CategoryChannel], 
                            overwrites: Dict[Any, discord.PermissionOverwrite]) -> tuple[Optional[discord.abc.GuildChannel], List[str]]:
        """Helper method to restore a channel"""
        logs = []
        try:
            channel_type = getattr(discord.ChannelType, channel_data['type'].split('.')[-1])
            category = category_map.get(channel_data.get('category_id'))

            if channel_type == discord.ChannelType.text:
                channel = await guild.create_text_channel(
                    name=channel_data['name'],
                    category=category,
                    topic=channel_data.get('topic'),
                    nsfw=channel_data.get('nsfw', False),
                    slowmode_delay=channel_data.get('slowmode_delay', 0),
                    position=channel_data['position'],
                    overwrites=overwrites
                )
                
                # Restore pins if they exist
                if 'pins' in channel_data and channel_data['pins']:
                    pin_logs = await self.restore_pins(channel, channel_data['pins'])
                    logs.extend(pin_logs)
                    
            elif channel_type == discord.ChannelType.voice:
                channel = await guild.create_voice_channel(
                    name=channel_data['name'],
                    category=category,
                    bitrate=channel_data.get('bitrate', 64000),
                    user_limit=channel_data.get('user_limit', 0),
                    position=channel_data['position'],
                    overwrites=overwrites
                )
            else:
                logger.warning(f"Unsupported channel type: {channel_type}")
                return None, [f"⚠️ Skipped unsupported channel type: {channel_type}"]

            logs.append(f"✅ Created channel: {channel.name}")
            return channel, logs

        except Exception as e:
            logger.error(f"Error restoring channel {channel_data['name']}: {e}")
            return None, [f"❌ Failed to create channel {channel_data['name']}: {e}"]

    async def restore_backup(self, guild: discord.Guild, backup_data: Dict[str, Any]) -> List[str]:
        """Restore a guild from backup data"""
        logs = []
        logs.append("Starting restore process...")

        try:
            # Delete existing roles and channels
            logs.append("Cleaning up existing server configuration...")
            
            # Delete non-default roles (keep @everyone)
            for role in guild.roles[1:]:
                try:
                    if role != guild.default_role and role < guild.me.top_role:
                        await role.delete()
                        logs.append(f"Deleted role: {role.name}")
                except discord.Forbidden:
                    logs.append(f"⚠️ Could not delete role: {role.name}")
                except Exception as e:
                    logs.append(f"⚠️ Error deleting role {role.name}: {e}")

            # Delete all channels
            for channel in guild.channels:
                try:
                    await channel.delete()
                    logs.append(f"Deleted channel: {channel.name}")
                except discord.Forbidden:
                    logs.append(f"⚠️ Could not delete channel: {channel.name}")
                except Exception as e:
                    logs.append(f"⚠️ Error deleting channel {channel.name}: {e}")

            # Create roles
            logs.append("Restoring roles...")
            role_map = {}  # Map old role IDs to new roles
            for role_data in sorted(backup_data['roles'], key=lambda r: r['position']):
                try:
                    new_role = await guild.create_role(
                        name=role_data['name'],
                        permissions=discord.Permissions(role_data['permissions']),
                        color=discord.Color(role_data['color']),
                        hoist=role_data['hoist'],
                        mentionable=role_data['mentionable']
                    )
                    role_map[role_data['id']] = new_role
                    logs.append(f"✅ Created role: {new_role.name}")
                except Exception as e:
                    logs.append(f"⚠️ Error creating role {role_data['name']}: {e}")

            # Create categories
            logs.append("Restoring categories...")
            category_map = {}  # Map old category IDs to new categories
            for cat_data in sorted(backup_data['categories'], key=lambda c: c['position']):
                try:
                    overwrites = self.deserialize_overwrites(cat_data['overwrites'], guild)
                    new_cat = await guild.create_category(
                        name=cat_data['name'],
                        overwrites=overwrites,
                        position=cat_data['position']
                    )
                    category_map[cat_data['id']] = new_cat
                    logs.append(f"✅ Created category: {new_cat.name}")
                except Exception as e:
                    logs.append(f"⚠️ Error creating category {cat_data['name']}: {e}")

            # Create channels
            logs.append("Restoring channels...")
            for channel_data in sorted(backup_data['channels'], key=lambda c: c['position']):
                try:
                    overwrites = self.deserialize_overwrites(channel_data['overwrites'], guild)
                    channel, channel_logs = await self.restore_channel(guild, channel_data, category_map, overwrites)
                    logs.extend(channel_logs)
                except Exception as e:
                    logs.append(f"⚠️ Error creating channel {channel_data['name']}: {e}")

            # Restore bot settings
            if 'bot_settings' in backup_data:
                logs.append("Restoring bot settings...")
                if 'incidents_channel_id' in backup_data['bot_settings']:
                    self.bot.incidents_channel_id = backup_data['bot_settings']['incidents_channel_id']
                if 'promotion_channel_id' in backup_data['bot_settings']:
                    self.bot.promotion_channel_id = backup_data['bot_settings']['promotion_channel_id']

            logs.append("✅ Restore process completed!")

        except Exception as e:
            logs.append(f"❌ Critical error during restore: {e}")
            logger.error(f"Critical error during restore: {e}")

        return logs

    @app_commands.command(name="draxon-backup", description="Create a backup of the server configuration")
    @app_commands.checks.has_role("Chairman")
    async def backup(self, interaction: discord.Interaction):
        """Create a backup of the server"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create backup
            backup_data = await self.create_backup(interaction.guild)
            
            # Convert to JSON and create file
            backup_json = json.dumps(backup_data, indent=2)
            file = discord.File(
                io.StringIO(backup_json),
                filename=f'draxon_backup_{datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
            )
            
            await interaction.followup.send(
                "✅ Backup created successfully! Here's your backup file:",
                file=file,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            await interaction.followup.send(
                f"❌ Error creating backup: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="draxon-restore", description="Restore server configuration from a backup file")
    @app_commands.checks.has_role("Chairman")
    async def restore(self, interaction: discord.Interaction, backup_file: discord.Attachment):
        """Restore from a backup file"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate file
            if not backup_file.filename.endswith('.json'):
                await interaction.followup.send("❌ Please provide a valid JSON backup file.", ephemeral=True)
                return
                
            # Read and validate backup data
            backup_content = await backup_file.read()
            backup_data = json.loads(backup_content.decode('utf-8'))
            
            # Confirm with user
            await interaction.followup.send(
                "⚠️ **Warning**: This will delete all current channels and roles before restoring from backup.\n"
                "Are you sure you want to proceed? Reply with `yes` to continue.",
                ephemeral=True
            )
            
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                
                if msg.content.lower() != 'yes':
                    await interaction.followup.send("❌ Restore cancelled.", ephemeral=True)
                    return
                
                # Send initial status message
                status_message = await interaction.followup.send(
                    "🔄 Starting restore process...",
                    ephemeral=True
                )
                
                # Perform restore
                logs = await self.restore_backup(interaction.guild, backup_data)
                
                # Send logs in chunks due to Discord message length limits
                log_chunks = [logs[i:i + 10] for i in range(0, len(logs), 10)]
                for index, chunk in enumerate(log_chunks, 1):
                    await interaction.followup.send(
                        f"**Restore Progress ({index}/{len(log_chunks)}):**\n" + 
                        '\n'.join(chunk),
                        ephemeral=True
                    )
                
                # Final status update
                await interaction.followup.send(
                    "✅ Restore process completed! Please verify all channels and roles.",
                    ephemeral=True
                )
                
            except asyncio.TimeoutError:
                await interaction.followup.send(
                    "❌ Confirmation timed out. Restore cancelled.",
                    ephemeral=True
                )
                
        except json.JSONDecodeError:
            await interaction.followup.send(
                "❌ Invalid backup file format. Please ensure the file is a valid JSON backup.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            await interaction.followup.send(
                f"❌ Error restoring backup: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    """Safe setup function for backup cog"""
    try:
        # Check if the cog is already loaded
        if not bot.get_cog('BackupCog'):
            await bot.add_cog(BackupCog(bot))
            logger.info('Backup cog loaded successfully')
        else:
            logger.info('Backup cog already loaded, skipping')
    except Exception as e:
        logger.error(f'Error loading backup cog: {e}')
        raise