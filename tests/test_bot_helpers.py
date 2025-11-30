"""
Unit tests for bot helper functions.
Tests reminder parsing and formatting logic.
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestBotHelpers(unittest.TestCase):
    """Test suite for bot helper functions."""

    def test_work_session_reminder_labels(self):
        """Test that work session reminder labels are defined."""
        from bot import WORK_SESSION_REMINDER_LABELS
        
        self.assertIn('24h', WORK_SESSION_REMINDER_LABELS)
        self.assertIn('1h', WORK_SESSION_REMINDER_LABELS)
        self.assertIn('now', WORK_SESSION_REMINDER_LABELS)
        
        self.assertIn('24-hour', WORK_SESSION_REMINDER_LABELS['24h'])
        self.assertIn('1-hour', WORK_SESSION_REMINDER_LABELS['1h'])

    def test_due_date_reminder_labels(self):
        """Test that due date reminder labels are defined."""
        from bot import DUE_DATE_REMINDER_LABELS
        
        self.assertIn('2d', DUE_DATE_REMINDER_LABELS)
        self.assertIn('1d', DUE_DATE_REMINDER_LABELS)
        self.assertIn('12h', DUE_DATE_REMINDER_LABELS)

    def test_due_date_reminder_messages(self):
        """Test that due date reminder messages are defined."""
        from bot import DUE_DATE_REMINDER_MESSAGES
        
        self.assertIn('2d', DUE_DATE_REMINDER_MESSAGES)
        self.assertIn('1d', DUE_DATE_REMINDER_MESSAGES)
        self.assertIn('12h', DUE_DATE_REMINDER_MESSAGES)
        
        self.assertIn('2 days', DUE_DATE_REMINDER_MESSAGES['2d'])
        self.assertIn('1 day', DUE_DATE_REMINDER_MESSAGES['1d'])
        self.assertIn('12 hours', DUE_DATE_REMINDER_MESSAGES['12h'])

    def test_parse_day_time_input_valid(self):
        """Test parsing valid day/time input."""
        from bot import parse_day_time_input
        
        monday = datetime(2025, 10, 13, 0, 0, 0)  # Monday
        
        # Test Wednesday 7:30 PM
        result = parse_day_time_input("Wed 7:30 PM", monday)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith('Z'))  # Should be UTC ISO format

    def test_parse_day_time_input_am(self):
        """Test parsing AM time."""
        from bot import parse_day_time_input
        
        monday = datetime(2025, 10, 13, 0, 0, 0)
        
        result = parse_day_time_input("Mon 9:00 AM", monday)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith('Z'))

    def test_parse_day_time_input_noon(self):
        """Test parsing 12 PM (noon)."""
        from bot import parse_day_time_input
        
        monday = datetime(2025, 10, 13, 0, 0, 0)
        
        result = parse_day_time_input("Fri 12:00 PM", monday)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith('Z'))

    def test_parse_day_time_input_midnight(self):
        """Test parsing 12 AM (midnight)."""
        from bot import parse_day_time_input
        
        monday = datetime(2025, 10, 13, 0, 0, 0)
        
        result = parse_day_time_input("Sat 12:00 AM", monday)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith('Z'))

    def test_parse_day_time_input_invalid_format(self):
        """Test that invalid format returns None."""
        from bot import parse_day_time_input
        
        monday = datetime(2025, 10, 13, 0, 0, 0)
        
        result = parse_day_time_input("Invalid input", monday)
        self.assertIsNone(result)

    def test_parse_day_time_input_invalid_day(self):
        """Test that invalid day name returns None."""
        from bot import parse_day_time_input
        
        monday = datetime(2025, 10, 13, 0, 0, 0)
        
        result = parse_day_time_input("XYZ 7:30 PM", monday)
        self.assertIsNone(result)

    def test_parse_day_time_input_various_day_formats(self):
        """Test parsing different day name formats."""
        from bot import parse_day_time_input
        
        monday = datetime(2025, 10, 13, 0, 0, 0)
        
        # Full name
        result1 = parse_day_time_input("Monday 9:00 AM", monday)
        self.assertIsNotNone(result1)
        self.assertIsInstance(result1, str)
        
        # Abbreviated
        result2 = parse_day_time_input("Tue 9:00 AM", monday)
        self.assertIsNotNone(result2)
        self.assertIsInstance(result2, str)
        
        # Alternative abbreviation
        result3 = parse_day_time_input("Thurs 9:00 AM", monday)
        self.assertIsNotNone(result3)
        self.assertIsInstance(result3, str)


if __name__ == "__main__":
    unittest.main()
