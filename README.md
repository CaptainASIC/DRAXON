# DraXon Discord Management System v1.6.0

This repository contains two complementary Discord bots designed for DraXon (DraXon Industries):
1. PULSE (Planetary & Universal Locator System for Emergencies) - Emergency management system
2. DraXon AI - Server management and RSI integration system

## DraXon AI Features

### Server Management
- Automated channel creation and management
- Dynamic channel statistics
- Server backup and restore functionality
- Role management system
- Automated role verification

### RSI Integration
- Account linking with RSI handles
- Organization member tracking
- Member verification system
- Main/Affiliate status tracking
- Member comparison tools
- Local database storage for quick lookups
- Daily account link reminders
- Automated affiliate role management

### Status Monitoring
- RSI Platform status tracking
- Real-time incident monitoring
- Automated status updates
- Dedicated status channels

### Role Management
- Promotion/demotion system
- Automated role assignments
- Role verification based on org status
- Multi-channel notification system
- Permission management

## Commands

### Basic Commands
- `/system-status` - Display current status of RSI systems
- `/draxon-link` - Link your RSI account with Discord
- `/draxon-org` - Display organization member list with roles
- `/draxon-compare` - Compare Discord members with RSI org members
- `/help` - Display all available commands

### Leadership Commands
- `/draxon-stats` - Display member statistics (Leadership)
- `/promote` - Promote a member (Leadership)
- `/demote` - Demote a member (Leadership)

### Management Commands
- `/refresh-channels` - Refresh channel information
- `/setup` - Configure bot channels and notifications
- `/force-check` - Check incidents and status
- `/DraXon-backup` - Create server backup
- `/DraXon-restore` - Restore from backup

## Installation

1. Clone the repository:
```bash
git clone https://github.com/CaptainASIC/DraXon
cd DraXon
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env/.env.example env/.env
```

5. Edit `env/.env` with your tokens:
```
DISCORD_TOKEN=your_pulse_bot_token_here
DraXon_AI_TOKEN=your_DraXon_ai_token_here
RSI_API_KEY=your_rsi_api_key_here
```

## Project Structure

```
DraXon/
├── env/                # Environment variables
├── logs/              # Log files
├── data/              # Database storage
├── lib/               # Shared libraries
│   ├── constants.py   # Shared constants
│   └── rsi_db.py      # RSI database handler
├── cogs/              # Bot cogs
├── pulse_bot.py       # PULSE bot code
├── DraXon_ai.py       # DraXon AI bot code
└── README.md          # Documentation
```

## New Features in v1.6.0

- **Daily Role Verification**: Automatically verifies and updates member roles based on organization status
- **Automated Affiliate Management**: Ensures affiliates maintain appropriate role levels
- **Account Link Reminders**: Daily reminders for unlinked members
- **Enhanced Notification System**: Multi-channel notifications for various events
- **Modal-Based Setup**: Improved channel configuration interface
- **Screening Role**: New role for unverified members
- **API Availability Handling**: Better handling of RSI API maintenance windows

## Database

The system uses SQLite for storing RSI member data. The database is automatically created at `data/rsi_members.db` and includes:
- Member information
- Organization status
- Verification data
- Linking history
- Role change history

## Contact

For questions about either bot, please contact:
- GitHub Issues: [Create an issue](https://github.com/CaptainASIC/DraXon/issues)
- DraXon Discord: [Join our server](https://discord.gg/bjFZBRhw8Q)

Created by DraXon (DraXon Industries)