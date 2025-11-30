"""
Regression tests for bot startup and initialization.
Ensures the bot can start without errors and doesn't hang.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestBotStartup(unittest.TestCase):
    """Regression tests for bot startup behavior."""

    def test_bot_module_imports_without_running(self):
        """
        REGRESSION: Bot used to run immediately on import, causing tests to hang.
        Ensure bot.py can be imported without starting the Discord bot.
        """
        try:
            import bot
            # If we get here, the bot didn't start (good!)
            self.assertIsNotNone(bot)
        except Exception as e:
            self.fail(f"Bot module failed to import: {e}")

    def test_bot_has_main_guard(self):
        """
        REGRESSION: Verify bot.run() is protected by if __name__ == "__main__".
        """
        import bot
        import inspect
        
        # Read the source file
        bot_source = inspect.getsource(bot)
        
        # Verify bot.run is protected
        self.assertIn('if __name__ == "__main__":', bot_source)
        self.assertIn('bot.run(BOT_TOKEN)', bot_source)

    def test_bot_constants_accessible(self):
        """
        REGRESSION: Ensure bot constants are accessible for testing.
        """
        from bot import (
            WORK_SESSION_REMINDER_LABELS,
            DUE_DATE_REMINDER_LABELS,
            DUE_DATE_REMINDER_MESSAGES
        )
        
        self.assertIsInstance(WORK_SESSION_REMINDER_LABELS, dict)
        self.assertIsInstance(DUE_DATE_REMINDER_LABELS, dict)
        self.assertIsInstance(DUE_DATE_REMINDER_MESSAGES, dict)

    def test_parse_day_time_input_returns_string(self):
        """
        REGRESSION: parse_day_time_input should return string (ISO timestamp), not datetime.
        Tests were originally written expecting datetime, but function returns string.
        """
        from bot import parse_day_time_input
        from datetime import datetime
        
        monday = datetime(2025, 10, 13, 0, 0, 0)
        result = parse_day_time_input("Mon 9:00 AM", monday)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str, "Should return ISO timestamp string")
        self.assertTrue(result.endswith('Z'), "Should be UTC ISO format")


if __name__ == "__main__":
    unittest.main()
