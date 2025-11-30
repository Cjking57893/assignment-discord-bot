"""
Integration tests for datetime utilities with Canvas data.
Tests datetime parsing and formatting in realistic scenarios.
"""

import unittest
from datetime import datetime, timezone, timedelta
from utils.datetime_utils import (
    parse_canvas_datetime,
    to_utc_iso_z,
    to_local,
    format_local,
    week_start_end_local,
    get_local_tz
)


class TestDatetimeIntegration(unittest.TestCase):
    """Integration tests for datetime utilities with Canvas workflows."""

    def test_canvas_datetime_round_trip(self):
        """Test parsing Canvas datetime and converting back to UTC ISO."""
        # Simulate Canvas API datetime
        canvas_datetime = "2025-10-15T14:30:00Z"
        
        # Parse it
        parsed = parse_canvas_datetime(canvas_datetime)
        
        # Convert back to UTC ISO
        result = to_utc_iso_z(parsed)
        
        # Should match original
        self.assertEqual(result, canvas_datetime)

    def test_timezone_conversion_workflow(self):
        """Test complete workflow: Canvas UTC -> Local -> Format -> Display."""
        # Canvas assignment due date (UTC)
        canvas_due_date = "2025-12-20T23:59:00Z"
        
        # Convert to local time
        local_dt = to_local(canvas_due_date)
        
        # Verify it's not UTC
        self.assertNotEqual(local_dt.tzinfo, timezone.utc)
        
        # Format for display
        formatted = format_local(canvas_due_date, "%B %d, %Y at %I:%M %p")
        
        # Should contain expected components
        self.assertIn("December", formatted)
        self.assertIn("20", formatted)
        self.assertIn("2025", formatted)

    def test_week_planning_scenario(self):
        """Test realistic week planning with multiple assignments."""
        # Student plans their week on Monday
        monday_reference = datetime(2025, 10, 13, 9, 0, 0, tzinfo=timezone.utc)
        
        # Get week boundaries
        week_start, week_end = week_start_end_local(monday_reference)
        
        # Week should be Monday to Sunday
        self.assertEqual(week_start.weekday(), 0)  # Monday
        self.assertEqual(week_end.weekday(), 6)   # Sunday
        
        # Week should span 7 days
        self.assertEqual((week_end - week_start).days, 6)
        
        # Start should be midnight
        self.assertEqual(week_start.hour, 0)
        self.assertEqual(week_start.minute, 0)
        
        # End should be 23:59
        self.assertEqual(week_end.hour, 23)
        self.assertEqual(week_end.minute, 59)

    def test_assignment_due_date_comparison(self):
        """Test comparing assignment due dates across timezones."""
        # Assignment 1: Due in UTC
        due_1 = parse_canvas_datetime("2025-12-15T23:59:00Z")
        
        # Assignment 2: Due earlier
        due_2 = parse_canvas_datetime("2025-12-14T23:59:00Z")
        
        # Assignment 3: Due later
        due_3 = parse_canvas_datetime("2025-12-16T23:59:00Z")
        
        # Comparisons should work correctly
        self.assertTrue(due_2 < due_1 < due_3)
        
        # Convert to local and comparisons should still work
        local_1 = to_local(due_1)
        local_2 = to_local(due_2)
        local_3 = to_local(due_3)
        
        self.assertTrue(local_2 < local_1 < local_3)

    def test_reminder_time_calculations(self):
        """Test calculating reminder times before assignment due dates."""
        # Assignment due date
        due_date_str = "2025-12-20T23:59:00Z"
        due_date = parse_canvas_datetime(due_date_str)
        
        # Calculate reminder times
        reminder_2d = due_date - timedelta(days=2)
        reminder_1d = due_date - timedelta(days=1)
        reminder_12h = due_date - timedelta(hours=12)
        
        # Convert to UTC ISO for storage
        reminder_2d_iso = to_utc_iso_z(reminder_2d)
        reminder_1d_iso = to_utc_iso_z(reminder_1d)
        reminder_12h_iso = to_utc_iso_z(reminder_12h)
        
        # Parse back and verify they're before due date
        self.assertTrue(parse_canvas_datetime(reminder_2d_iso) < due_date)
        self.assertTrue(parse_canvas_datetime(reminder_1d_iso) < due_date)
        self.assertTrue(parse_canvas_datetime(reminder_12h_iso) < due_date)
        
        # Verify time differences
        self.assertAlmostEqual(
            (due_date - parse_canvas_datetime(reminder_2d_iso)).total_seconds(),
            2 * 24 * 3600,
            delta=1
        )

    def test_study_session_planning_times(self):
        """Test planning study sessions at specific times during the week."""
        # Get current week
        monday, sunday = week_start_end_local()
        
        # Plan study sessions
        sessions = []
        tz = get_local_tz()
        
        # Monday 2 PM
        mon_session = monday.replace(hour=14, minute=0, second=0, tzinfo=tz)
        sessions.append(to_utc_iso_z(mon_session))
        
        # Wednesday 7 PM
        wed_session = (monday + timedelta(days=2)).replace(hour=19, minute=0, second=0, tzinfo=tz)
        sessions.append(to_utc_iso_z(wed_session))
        
        # Friday 10 AM
        fri_session = (monday + timedelta(days=4)).replace(hour=10, minute=0, second=0, tzinfo=tz)
        sessions.append(to_utc_iso_z(fri_session))
        
        # All sessions should be within the week
        for session_iso in sessions:
            session_dt = to_local(session_iso)
            self.assertTrue(monday <= session_dt <= sunday)

    def test_multiple_timezone_formats(self):
        """Test handling different timezone formats from Canvas."""
        # Different formats Canvas might return
        formats = [
            "2025-10-15T14:30:00Z",           # Z format
            "2025-10-15T14:30:00+00:00",      # +00:00 format
            "2025-10-15T14:30:00.000Z",       # With milliseconds
        ]
        
        parsed_times = [parse_canvas_datetime(fmt) for fmt in formats]
        
        # All should parse to the same time
        base_time = parsed_times[0]
        for parsed in parsed_times[1:]:
            # Allow for microsecond differences
            self.assertAlmostEqual(
                parsed.timestamp(),
                base_time.timestamp(),
                delta=1
            )

    def test_week_boundary_edge_cases(self):
        """Test week calculations at week boundaries."""
        # Sunday night (last moment of week)
        sunday_night = datetime(2025, 10, 19, 23, 59, 0, tzinfo=timezone.utc)
        mon1, sun1 = week_start_end_local(sunday_night)
        
        # Monday morning (first moment of next week)
        monday_morning = datetime(2025, 10, 20, 0, 1, 0, tzinfo=timezone.utc)
        mon2, sun2 = week_start_end_local(monday_morning)
        
        # Should be different weeks
        self.assertNotEqual(mon1.date(), mon2.date())
        self.assertEqual((mon2 - mon1).days, 7)

    def test_assignment_overdue_detection(self):
        """Test detecting if assignments are overdue."""
        # Current time
        now = datetime.now(timezone.utc)
        
        # Past due date
        past_due = to_utc_iso_z(now - timedelta(days=1))
        past_dt = parse_canvas_datetime(past_due)
        self.assertTrue(past_dt < now)
        
        # Future due date
        future_due = to_utc_iso_z(now + timedelta(days=1))
        future_dt = parse_canvas_datetime(future_due)
        self.assertTrue(future_dt > now)
        
        # Due in exactly 12 hours
        twelve_hours = to_utc_iso_z(now + timedelta(hours=12))
        twelve_dt = parse_canvas_datetime(twelve_hours)
        time_until_due = (twelve_dt - now).total_seconds() / 3600
        self.assertAlmostEqual(time_until_due, 12, delta=0.1)


if __name__ == "__main__":
    unittest.main()
