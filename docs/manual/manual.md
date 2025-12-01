---
marp: true
html: true
theme: default
size: 16:9
paginate: true
footer: 'Assignment Discord Bot - User Manual'
---

# Assignment Discord Bot - User Manual

**Version 1.0**  
**Last Updated:** November 2025

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Bot Permissions](#bot-permissions)
4. [Core Features](#core-features)
5. [Commands](#commands)
6. [Weekly Summary](#weekly-summary)
7. [Reminders](#reminders)
8. [Data & Sync](#data--sync)
9. [Settings](#settings)
10. [Troubleshooting](#troubleshooting)
11. [Support & Feedback](#support--feedback)

---

## Introduction

Welcome to the **Assignment Discord Bot**! This bot helps classes and study groups stay on top of assignments by syncing from Canvas, posting a weekly summary, and sending gentle reminders for work sessions and due dates.

### Key Features

✅ **Canvas Sync** – Pulls courses and assignments from Canvas  
✅ **Weekly Summary** – Posts a Monday overview of upcoming items  
✅ **Work Session Reminders** – Nudges you when planned study times start  
✅ **Due Date Alerts** – Reminds you ahead of assignment deadlines  
✅ **Completion Flow** – Mark items complete to stop reminders  
✅ **Timezone-Aware** – Stores in UTC, presents in your timezone

---

## Getting Started

### Prerequisites

- A Discord server with permissions to add bots
- A Canvas account and API token
- Python 3.9+ on your host machine

### Setup

1. Create a `.env` file based on `.env.example` and set:  
	 - `BOT_TOKEN`, `CHANNEL_ID`, `CANVAS_TOKEN`, `CANVAS_BASE_URL`, `TIMEZONE`  
2. Install dependencies:  
	 ```powershell
	 pip install -r requirements.txt
	 ```
3. Run the bot:  
	 ```powershell
	 python bot.py
	 ```

> Notes: The bot stores data in a local SQLite database; first run initializes the schema automatically.

---

## Bot Permissions

- Recommended Discord permissions for the bot role:  
	- Read Messages / View Channels  
	- Send Messages  
	- Embed Links  
	- Add Reactions (optional)  
	- Manage Messages (optional, for tidy-ups)  

Ensure the target `CHANNEL_ID` is visible to the bot.

---

## Core Features

- **Canvas Integration**: Fetches courses and assignments via the Canvas API.  
- **Weekly Overview**: Summarizes upcoming assignments every Monday.  
- **Interactive Planning**: Users can set preferred study day/time.  
- **Smart Reminders**: Sends pings for planned sessions and upcoming due dates.  
- **Completion Tracking**: Mark assignments complete to stop future reminders.

---

## Commands

Below are common commands (exact names may vary by server setup):

- **`sync`**: Fetch the latest assignments from Canvas and update the database.  
- **`thisweek`**: Show this week’s assignments (summary in-channel).  
- **`plans`**: Start an interactive flow to set your weekly study day/time.  
- **`complete <assignment_id>`**: Mark an assignment as complete.  
- **`reschedule`**: Update your planned day/time for work sessions.  

> Tip: Use `thisweek` after `sync` to confirm the latest items.

---

## Weekly Summary

- The bot posts a summary every Monday to the configured channel.  
- It groups assignments by course and highlights due dates.  
- Timezones are respected for display; data is stored in UTC.

---

## Reminders

- **Work Session Reminders**:  
	- Triggered at your planned day/time.  
	- Sent once per session to avoid spam.  
- **Due Date Alerts**:  
	- Sent ahead of assignment deadlines based on configured lead times.  
	- Suppressed once the assignment is marked complete.

You can adjust your schedule via `plans` or `reschedule`.

---

## Data & Sync

- **Canvas Sync**:  
	- Uses `canvas_api` module and pagination for large result sets.  
	- Handles transient API errors gracefully.  
- **Database**:  
	- SQLite with async access; schema and migrations managed automatically.  
	- Stores assignments, user plans, and reminder flags.  
- **Timezone Handling**:  
	- Datetimes stored in UTC; presented in `TIMEZONE` from environment.

---

## Settings

Key environment variables (see `.env.example`):

- `BOT_TOKEN`: Discord bot token  
- `CHANNEL_ID`: Channel ID for posts and reminders  
- `CANVAS_TOKEN`: Canvas API token (Bearer)  
- `CANVAS_BASE_URL`: Canvas base URL (e.g., `https://canvas.instructure.com`)  
- `DB_PATH`: Optional custom SQLite path  
- `TIMEZONE`: IANA timezone (e.g., `America/New_York`)  
- `WEEKLY_NOTIFICATION_HOUR` / `WEEKLY_NOTIFICATION_MINUTE`: Post time on Mondays

---

## Troubleshooting

- **No messages appear**:  
	- Confirm `BOT_TOKEN`, bot permissions, and `CHANNEL_ID`.  
- **Canvas sync fails**:  
	- Verify `CANVAS_TOKEN` and `CANVAS_BASE_URL`; check network connectivity.  
- **Wrong times shown**:  
	- Ensure `TIMEZONE` is set correctly; restart the bot after changes.  
- **Duplicate reminders**:  
	- Mark items complete; if issues persist, run `sync` and check DB state.

---

## Support & Feedback

For help or suggestions:

- Open an issue in the repository  
- Share feedback in the bot’s Discord channel  
- Provide assignment IDs and context when reporting reminder issues

---

_Thanks for using the Assignment Discord Bot! Stay organized and on track._

