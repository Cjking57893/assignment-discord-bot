# Assignment Discord Bot

## Setup & Installation

### Prerequisites
- Python 3.9 or higher (for `zoneinfo` support)
- A Discord Bot Token (from Discord Developer Portal)
- A Canvas API Token (from Canvas Settings)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd assignment-discord-bot
```

### 2. Install Required Python Packages
```bash
pip install discord.py python-dotenv aiosqlite requests
```

Or create a `requirements.txt` with:
```
discord.py>=2.0.0
python-dotenv>=0.19.0
aiosqlite>=0.17.0
requests>=2.28.0
```
Then run: `pip install -r requirements.txt`

### 3. Configure Environment Variables
Create a `.env` file in the root directory with the following:

```env
BOT_TOKEN=your_discord_bot_token_here
CANVAS_TOKEN=your_canvas_api_token_here
CHANNEL_ID=your_discord_channel_id_here
```

**Where to get these:**
- **BOT_TOKEN**: Create a Discord bot at [Discord Developer Portal](https://discord.com/developers/applications)
  - Go to "Bot" section → Reset Token → Copy the token
  - Enable "Message Content Intent" under Privileged Gateway Intents
- **CANVAS_TOKEN**: Canvas → Account → Settings → "+ New Access Token"
- **CHANNEL_ID**: Right-click on your Discord channel → Copy Channel ID (requires Developer Mode enabled in Discord settings)

**Note:** The database will be automatically created at `data/canvas_bot.db` when you first run the bot. If you have an existing database, place it in the `data/` directory.

### 4. Invite Bot to Your Discord Server
1. Go to Discord Developer Portal → Your Application → OAuth2 → URL Generator
2. Select scopes: `bot`
3. Select bot permissions: `Send Messages`, `Read Message History`, `Read Messages/View Channels`
4. Copy the generated URL and open it in your browser to invite the bot

### 5. Run the Bot
```bash
python bot.py
```

The bot will:
- Automatically create the `data/` directory if it doesn't exist
- Initialize the SQLite database
- Perform an initial sync with Canvas
- Start listening for Discord commands
- **Send weekly assignment notifications every Monday at 9:00 AM** to the configured channel

## Features

### Automatic Weekly Notifications
Every Monday at 9:00 AM, the bot will:
1. Sync with Canvas to fetch the latest assignments
2. Send a message to the configured channel listing all assignments due that week
3. Users can then use `!thisweek` to interactively schedule work times

### Manual Commands

- !sync — Sync courses and assignments from Canvas into the local database.
- !thisweek — List assignments due this week (Mon–Sun) and schedule study sessions for each.
- !plans — Show your planned study sessions for the current week.
 - !complete — Mark incomplete assignments for this week as completed (interactive selection or provide a name query).

Notes

- Timezone: Timestamps are stored in UTC in the database and shown in your local timezone when displayed in Discord. You can set TIMEZONE in your environment to override auto-detection.
 - Pagination: Canvas API requests use per_page=100 and follow Link headers, so all your courses/assignments should be included.