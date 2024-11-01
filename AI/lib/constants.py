from pathlib import Path

# Version info
APP_VERSION = "1.6.1"  # Incremented for enhanced promotion system
BUILD_DATE = "Oct 2024"

# Configuration
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10  # seconds
HEADERS = {
    'User-Agent': 'DraXon_AI_Bot/1.6.1'
}

# Setup directories
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
ENV_DIR = BASE_DIR / "env"
DB_DIR = BASE_DIR / "data"  # Database directory

# Define DraXon role hierarchy
DraXon_ROLES = {
    'leadership': ['Chairman', 'Director'],
    'management': ['Manager', 'Team Leader'],
    'staff': ['Employee'],
    'restricted': ['Applicant', 'Screening']
}

# Role hierarchy order (ascending)
ROLE_HIERARCHY = [
    'Screening',
    'Applicant',
    'Employee',
    'Team Leader',
    'Manager',
    'Director',
    'Chairman'
]

# Role Management Configuration
LEADERSHIP_MAX_RANK = "Team Leader"  # Maximum rank for affiliates
DEFAULT_DEMOTION_RANK = "Employee"   # Rank to demote affiliates to
UNAFFILIATED_RANK = "Screening"      # Rank for members not in org
MAX_PROMOTION_OPTIONS = 2            # Maximum number of ranks to show for promotion
PROMOTION_TIMEOUT = 180              # Seconds before promotion view times out

# Promotion System Messages
PROMOTION_MESSAGES = {
    'no_members': "❌ No members available for promotion.",
    'no_promotion': "❌ No promotion available for this member.",
    'member_first': "❌ Please select a member first.",
    'member_not_found': "❌ Selected member not found.",
    'role_not_found': "❌ Could not find the specified role.",
    'channel_config': "❌ Promotion channel not configured. Please use `/setup` first.",
    'success': "✅ Successfully promoted {member} to {rank}!",
    'error': "❌ An error occurred during the promotion process.",
    'system_error': "❌ Promotion system is currently unavailable.",
    'no_demotion': "❌ No demotion available for this member.",
    'no_members_demotion': "❌ No members available for demotion.",
    'demotion_success': "✅ Successfully demoted {member} to {rank}!"
}

# Timing Configuration
DAILY_CHECK_TIME = "12:00"  # UTC time for daily checks
REMINDER_COOLDOWN = 24      # Hours between reminders
API_MAINTENANCE_START = "22:00"  # UTC time when API typically goes down
API_MAINTENANCE_DURATION = 3     # Hours of typical maintenance

# Bot Permission Requirements
BOT_REQUIRED_PERMISSIONS = [
    'view_channel',
    'manage_channels',
    'manage_roles',
    'send_messages',
    'read_message_history',
    'create_private_threads',
    'read_messages',
    'move_members',
    'manage_messages',
    'attach_files',
    'send_messages_in_threads'
]

# Status emojis
STATUS_EMOJIS = {
    'operational': '✅',
    'degraded': '⚠️',
    'partial': '⚠️',
    'major': '❌',
    'maintenance': '🔧'
}

# Channel configuration
CATEGORY_NAME = "🖥️ DraXon AI 🖥️"
CHANNELS_CONFIG = [
    {
        "name": "all-staff",
        "display": "👥 All Staff: {count}",
        "count_type": "members"
    },
    {
        "name": "automated-systems",
        "display": "🤖 Automated Systems: {count}",
        "count_type": "bots"
    },
    {
        "name": "platform-status",
        "display": "{emoji} RSI Platform",
        "count_type": "status"
    },
    {
        "name": "persistent-universe-status",
        "display": "{emoji} Star Citizen (PU)",
        "count_type": "status"
    },
    {
        "name": "electronic-access-status",
        "display": "{emoji} Arena Commander",
        "count_type": "status"
    }
]

# Permission configurations
CHANNEL_PERMISSIONS = {
    'display_only': {
        'everyone': {
            'view_channel': True,
            'connect': False,
            'speak': False,
            'send_messages': False,
            'stream': False,
            'use_voice_activation': False
        },
        'bot': {
            'view_channel': True,
            'manage_channels': True,
            'manage_permissions': True,
            'connect': True,
            'manage_roles': True,
            'manage_messages': True,
            'attach_files': True,
            'send_messages_in_threads': True
        }
    }
}

# RSI API Configuration
RSI_API_BASE_URL = "https://api.starcitizen-api.com"
RSI_API_VERSION = "v1"
RSI_API_MODE = "live"
RSI_ORGANIZATION_SID = "DRAXON"  # Organization SID
RSI_MEMBERS_PER_PAGE = 32  # API pagination size

# Database Configuration
RSI_DB_PATH = DB_DIR / "rsi_members.db"

# Comparison Status Emojis
COMPARE_STATUS = {
    'match': '✅',      # Member found in both Discord and RSI
    'mismatch': '❌',   # Different data between Discord and RSI
    'missing': '⚠️'     # Missing from either Discord or RSI
}

# Message Templates
UNLINKED_REMINDER_MESSAGE = """
👋 Hello! This is a friendly reminder to link your RSI account with our Discord server.

You can do this by using the `/draxon-link` command in any channel.

Linking your account helps us maintain proper organization structure and ensures 
you have access to all appropriate channels and features.
"""

DEMOTION_MESSAGES = {
    'affiliate': "Affiliate status incompatible with leadership role",
    'not_in_org': "Not found in organization",
    'role_update': "Role updated due to organization status change"
}