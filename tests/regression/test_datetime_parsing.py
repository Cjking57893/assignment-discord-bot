"""
Regression tests for datetime parsing and conversion.
Ensures datetime handling remains consistent and correct.
"""

import unittest
from datetime import datetime, timezone, timedelta
from utils.datetime_utils import (
    parse_canvas_datetime,
    to_utc_iso_z,
    to_local,
    format_local,
    week_start_end_local
)


class TestDatetimeParsingRegression(unittest.TestCase):
    """Regression tests for datetime parsing stability."""

    def test_parse_canvas_datetime_handles_z_suffix(self):
        """
        REGRESSION: Ensure Canvas datetime strings with 'Z' suffix parse correctly.
        """
        dt_str = "2025-10-15T14:30:00Z"
        result = parse_canvas_datetime(dt_str)
        
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 10)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_to_utc_iso_z_always_ends_with_z(self):
        """
        REGRESSION: to_utc_iso_z should always produce strings ending with 'Z'.
        """
        dt = datetime(2025, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = to_utc_iso_z(dt)
        
        self.assertTrue(result.endswith('Z'))
        self.assertNotIn('+', result)
        self.assertNotIn('T00:00:00', result.split('T')[1])  # Not naive conversion

    def test_to_utc_iso_z_strips_microseconds(self):
        """
        REGRESSION: Microseconds should be stripped from output.
        Canvas API doesn't use microseconds.
        """
        dt = datetime(2025, 10, 15, 14, 30, 0, 123456, tzinfo=timezone.utc)
        result = to_utc_iso_z(dt)
        
        self.assertEqual(result, "2025-10-15T14:30:00Z")
        self.assertNotIn('123456', result)
        self.assertNotIn('.', result)

    def test_week_start_end_returns_monday_and_sunday(self):
        """
        REGRESSION: week_start_end_local should return Monday start and Sunday end.
        """
        ref = datetime(2025, 10, 15, 14, 30, 0, tzinfo=timezone.utc)  # Wednesday
        monday, sunday = week_start_end_local(ref)
        
        self.assertEqual(monday.weekday(), 0)  # Monday
        self.assertEqual(sunday.weekday(), 6)  # Sunday
        self.assertEqual((sunday - monday).days, 6)

    def test_week_boundaries_are_midnight_and_2359(self):
        """
        REGRESSION: Week should start at Monday 00:00 and end at Sunday 23:59.
        """
        ref = datetime(2025, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        monday, sunday = week_start_end_local(ref)
        
        self.assertEqual(monday.hour, 0)
        self.assertEqual(monday.minute, 0)
        self.assertEqual(monday.second, 0)
        
        self.assertEqual(sunday.hour, 23)
        self.assertEqual(sunday.minute, 59)
        self.assertEqual(sunday.second, 59)

    def test_empty_string_raises_valueerror(self):
        """
        REGRESSION: Parsing empty Canvas datetime should raise ValueError.
        """
        with self.assertRaises(ValueError):
            parse_canvas_datetime("")

    def test_format_local_default_includes_year(self):
        """
        REGRESSION: Default format should include year for clarity.
        """
        dt_str = "2025-10-15T14:30:00Z"
        result = format_local(dt_str)
        
        self.assertIn("2025", result)

    def test_naive_datetime_gets_local_timezone(self):
        """
        REGRESSION: Naive datetimes should be treated as local time.
        """
        naive_dt = datetime(2025, 10, 15, 14, 30, 0)
        result = to_utc_iso_z(naive_dt)
        
        # Should convert to UTC and end with Z
        self.assertTrue(result.endswith('Z'))
        self.assertIn("2025-10-15", result)


class TestTimezoneConsistencyRegression(unittest.TestCase):
    """Regression tests for timezone handling consistency."""

    def test_round_trip_preserves_time(self):
        """
        REGRESSION: Canvas datetime -> parse -> to_utc_iso_z should preserve the time.
        """
        original = "2025-10-15T14:30:00Z"
        parsed = parse_canvas_datetime(original)
        result = to_utc_iso_z(parsed)
        
        self.assertEqual(original, result)

    def test_to_local_returns_timezone_aware(self):
        """
        REGRESSION: to_local should always return timezone-aware datetime.
        """
        dt_str = "2025-10-15T14:30:00Z"
        result = to_local(dt_str)
        
        self.assertIsNotNone(result.tzinfo)
        self.assertNotEqual(result.tzinfo, timezone.utc)

    def test_different_offset_formats_parse_correctly(self):
        """
        REGRESSION: Various timezone offset formats should parse.
        """
        formats = [
            "2025-10-15T14:30:00Z",
            "2025-10-15T14:30:00+00:00",
            "2025-10-15T14:30:00-00:00"
        ]
        
        results = [parse_canvas_datetime(fmt) for fmt in formats]
        
        # All should parse to same UTC time
        for result in results:
            self.assertEqual(result.tzinfo, timezone.utc)
            self.assertEqual(result.hour, 14)
            self.assertEqual(result.minute, 30)


if __name__ == "__main__":
    unittest.main()
