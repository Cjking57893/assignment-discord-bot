# Assignment Discord Bot

A Discord bot that syncs Canvas assignments and sends automated reminders.

## Setup

### Prerequisites
- Python 3.9+
- Discord Bot Token
- Canvas API Token

### Installation

1. Clone and install dependencies:
```bash
git clone <repository-url>
cd assignment-discord-bot
pip install -r requirements.txt
```

2. Create `.env` file:
```env
BOT_TOKEN=your_discord_bot_token
CANVAS_TOKEN=your_canvas_api_token
CHANNEL_ID=your_discord_channel_id
```

Optional configuration:
```env
CANVAS_BASE_URL=https://canvas.instructure.com/api/v1/
WEEKLY_NOTIFICATION_HOUR=9
WEEKLY_NOTIFICATION_MINUTE=0
TIMEZONE=America/New_York
```

3. Run the bot:
```bash
python bot.py
```

## Features

- **Weekly notifications** - Automatic Monday morning assignment list
- **Work session reminders** - 24h, 1h, and at-time reminders for planned sessions
- **Due date reminders** - 2d, 1d, and 12h warnings before assignments are due
- **Completion tracking** - Mark assignments complete and get celebration messages

## Commands

- `!sync` - Sync Canvas data to local database
- `!thisweek` - List and schedule work sessions for this week's assignments
- `!plans` - Show your planned study sessions
- `!complete [query]` - Mark assignments as complete
- `!reschedule` - Change a planned session time

## Notes

- Times stored in UTC, displayed in local timezone
- Database auto-created at `data/canvas_bot.db`
- Reminders checked every minute
