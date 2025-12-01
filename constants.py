"""Application constants."""

# Reminder labels and messages
WORK_SESSION_REMINDER_LABELS = {
    '24h': '⏰ **24-hour reminder**',
    '1h': '⏰ **1-hour reminder**',
    'now': '🔔 **It\'s time!**'
}

DUE_DATE_REMINDER_LABELS = {
    '2d': '📅 **2-day reminder**',
    '1d': '📅 **1-day reminder**',
    '12h': '⚠️ **12-hour reminder**'
}

DUE_DATE_REMINDER_MESSAGES = {
    '2d': "💡 You have 2 days to complete this assignment!",
    '1d': "⚡ Only 1 day left to complete this assignment!",
    '12h': "🚨 Only 12 hours left! Time to finish up!"
}

# Day name mapping
DAY_NAME_MAP = {
    'mon': 0, 'monday': 0,
    'tue': 1, 'tues': 1, 'tuesday': 1,
    'wed': 2, 'wednesday': 2,
    'thu': 3, 'thurs': 3, 'thursday': 3,
    'fri': 4, 'friday': 4,
    'sat': 5, 'saturday': 5,
    'sun': 6, 'sunday': 6,
}

# Timeouts (in seconds)
SCHEDULING_TIMEOUT = 120.0
USER_RESPONSE_TIMEOUT = 90.0
RESCHEDULE_TIMEOUT = 120.0

# Background task settings
REMINDER_CHECK_INTERVAL = 1
DEFAULT_PER_PAGE = 100

