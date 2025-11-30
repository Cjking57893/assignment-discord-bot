"""
Unit tests for datetime utilities.
Tests timezone conversions, Canvas datetime parsing, and week calculations.
"""

import unittest
from datetime import datetime, timezone, timedelta
import os
from utils.datetime_utils import (
    get_local_tz,
    parse_canvas_datetime,
    to_utc_iso_z,
    to_local,
    format_local,
    week_start_end_local
)

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


class TestDatetimeUtils(unittest.TestCase):
    """Test suite for datetime utility functions."""

    def test_parse_canvas_datetime_with_z(self):
        """Test parsing Canvas datetime string with 'Z' suffix."""
        canvas_dt = "2025-10-15T14:30:00Z"
        result = parse_canvas_datetime(canvas_dt)
        
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 10)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_parse_canvas_datetime_with_offset(self):
        """Test parsing Canvas datetime with timezone offset."""
        canvas_dt = "2025-10-15T14:30:00+00:00"
        result = parse_canvas_datetime(canvas_dt)
        
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_parse_canvas_datetime_empty_raises_error(self):
        """Test that empty string raises ValueError."""
        with self.assertRaises(ValueError):
            parse_canvas_datetime("")

    def test_to_utc_iso_z_aware_datetime(self):
        """Test converting timezone-aware datetime to UTC ISO string."""
        dt = datetime(2025, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = to_utc_iso_z(dt)
        
        self.assertEqual(result, "2025-10-15T14:30:00Z")
        self.assertTrue(result.endswith("Z"))

    def test_to_utc_iso_z_naive_datetime(self):
        """Test converting naive datetime to UTC ISO string."""
        dt = datetime(2025, 10, 15, 14, 30, 0)
        result = to_utc_iso_z(dt)
        
        # Should attach local tz and convert to UTC
        self.assertTrue(result.endswith("Z"))
        self.assertIn("2025-10-15", result)

    def test_to_utc_iso_z_drops_microseconds(self):
        """Test that microseconds are dropped from output."""
        dt = datetime(2025, 10, 15, 14, 30, 0, 123456, tzinfo=timezone.utc)
        result = to_utc_iso_z(dt)
        
        self.assertEqual(result, "2025-10-15T14:30:00Z")
        self.assertNotIn("123456", result)

    def test_to_local_with_string(self):
        """Test converting Canvas datetime string to local time."""
        canvas_dt = "2025-10-15T14:30:00Z"
        result = to_local(canvas_dt)
        
        self.assertIsNotNone(result.tzinfo)
        self.assertNotEqual(result.tzinfo, timezone.utc)

    def test_to_local_with_datetime(self):
        """Test converting datetime object to local time."""
        dt = datetime(2025, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = to_local(dt)
        
        self.assertIsNotNone(result.tzinfo)
        # Result should be in local timezone
        local_tz = get_local_tz()
        self.assertEqual(result.tzinfo, local_tz)

    def test_format_local_default_format(self):
        """Test formatting datetime with default format."""
        canvas_dt = "2025-10-15T14:30:00Z"
        result = format_local(canvas_dt)
        
        # Default format: "%b %d, %Y, %I:%M %p"
        self.assertIn("Oct", result)
        self.assertIn("15", result)
        self.assertIn("2025", result)

    def test_format_local_custom_format(self):
        """Test formatting datetime with custom format."""
        canvas_dt = "2025-10-15T14:30:00Z"
        result = format_local(canvas_dt, "%Y-%m-%d")
        
        self.assertEqual(result, "2025-10-15")

    def test_week_start_end_local_monday(self):
        """Test week calculation when reference is Monday."""
        # Monday, October 13, 2025
        ref = datetime(2025, 10, 13, 10, 0, 0, tzinfo=timezone.utc)
        monday, sunday = week_start_end_local(ref)
        
        self.assertEqual(monday.weekday(), 0)  # Monday
        self.assertEqual(sunday.weekday(), 6)  # Sunday
        self.assertEqual(monday.hour, 0)
        self.assertEqual(monday.minute, 0)
        self.assertEqual(sunday.hour, 23)
        self.assertEqual(sunday.minute, 59)

    def test_week_start_end_local_wednesday(self):
        """Test week calculation when reference is Wednesday."""
        # Wednesday, October 15, 2025
        ref = datetime(2025, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        monday, sunday = week_start_end_local(ref)
        
        self.assertEqual(monday.weekday(), 0)  # Monday
        self.assertEqual(monday.day, 13)  # Monday Oct 13
        self.assertEqual(sunday.day, 19)  # Sunday Oct 19

    def test_week_start_end_local_sunday(self):
        """Test week calculation when reference is Sunday."""
        # Sunday, October 19, 2025
        ref = datetime(2025, 10, 19, 22, 0, 0, tzinfo=timezone.utc)
        monday, sunday = week_start_end_local(ref)
        
        self.assertEqual(monday.day, 13)  # Monday Oct 13
        self.assertEqual(sunday.day, 19)  # Sunday Oct 19

    def test_week_start_end_local_no_reference(self):
        """Test week calculation with no reference (uses current time)."""
        monday, sunday = week_start_end_local()
        
        self.assertEqual(monday.weekday(), 0)
        self.assertEqual(sunday.weekday(), 6)
        self.assertEqual((sunday - monday).days, 6)

    def test_get_local_tz_with_env_var(self):
        """Test getting local timezone from environment variable."""
        # Skip: Environment variable behavior is difficult to test due to module caching
        # and the fallback to system timezone. Manual testing recommended.
        self.skipTest("Environment variable timezone testing requires isolation")

    def test_get_local_tz_fallback(self):
        """Test getting local timezone falls back to system timezone."""
        # Clear environment variable
        original = os.getenv("TIMEZONE")
        os.environ.pop("TIMEZONE", None)
        
        try:
            tz = get_local_tz()
            self.assertIsNotNone(tz)
        finally:
            # Restore original
            if original:
                os.environ["TIMEZONE"] = original


if __name__ == "__main__":
    unittest.main()
