# Assignment Discord Bot

Commands

- !sync — Sync courses and assignments from Canvas into the local database.
- !thisweek — List assignments due this week (Mon–Sun) and schedule study sessions for each.
- !plans — Show your planned study sessions for the current week.
 - !complete — Mark incomplete assignments for this week as completed (interactive selection or provide a name query).

Notes

- Timezone: Timestamps are stored in UTC in the database and shown in your local timezone when displayed in Discord. You can set TIMEZONE in your environment to override auto-detection.
 - Pagination: Canvas API requests use per_page=100 and follow Link headers, so all your courses/assignments should be included.