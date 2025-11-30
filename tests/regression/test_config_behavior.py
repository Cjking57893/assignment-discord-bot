"""
Regression tests for configuration behavior.
Ensures configuration uses environment variables instead of hardcoded values.
"""

import unittest
import os
from unittest.mock import patch


class TestConfigRegression(unittest.TestCase):
    """Regression tests for configuration management."""

    def test_canvas_base_url_uses_env_var(self):
        """
        REGRESSION: CANVAS_BASE_URL was hardcoded to canvas.instructure.com.
        Now it should read from environment variable with fallback.
        """
        with patch.dict(os.environ, {'CANVAS_BASE_URL': 'https://custom.canvas.edu/api/v1/'}):
            # Reload config to pick up new env var
            import importlib
            import config
            importlib.reload(config)
            
            self.assertEqual(config.CANVAS_BASE_URL, 'https://custom.canvas.edu/api/v1/')

    def test_canvas_base_url_has_default(self):
        """
        REGRESSION: Ensure CANVAS_BASE_URL has a sensible default.
        """
        import config
        
        # Even without env var, should have a default
        self.assertIsNotNone(config.CANVAS_BASE_URL)
        self.assertIn('canvas', config.CANVAS_BASE_URL.lower())

    def test_db_path_uses_env_var(self):
        """
        REGRESSION: DB_PATH was hardcoded in db_manager.py.
        Now it should read from config which uses environment variable.
        """
        with patch.dict(os.environ, {'DB_PATH': 'custom/path/db.sqlite'}):
            import importlib
            import config
            importlib.reload(config)
            
            self.assertEqual(config.DB_PATH, 'custom/path/db.sqlite')

    def test_weekly_notification_time_configurable(self):
        """
        REGRESSION: Weekly notification time was hardcoded to 9:00 AM.
        Now it should be configurable via environment variables.
        """
        with patch.dict(os.environ, {
            'WEEKLY_NOTIFICATION_HOUR': '15',
            'WEEKLY_NOTIFICATION_MINUTE': '30'
        }):
            import importlib
            import config
            importlib.reload(config)
            
            self.assertEqual(config.WEEKLY_NOTIFICATION_HOUR, 15)
            self.assertEqual(config.WEEKLY_NOTIFICATION_MINUTE, 30)

    def test_weekly_notification_time_has_defaults(self):
        """
        REGRESSION: Ensure weekly notification time has sensible defaults.
        """
        # Remove env vars if they exist
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)
            
            # Should have defaults
            self.assertIsInstance(config.WEEKLY_NOTIFICATION_HOUR, int)
            self.assertIsInstance(config.WEEKLY_NOTIFICATION_MINUTE, int)
            self.assertGreaterEqual(config.WEEKLY_NOTIFICATION_HOUR, 0)
            self.assertLess(config.WEEKLY_NOTIFICATION_HOUR, 24)


if __name__ == "__main__":
    unittest.main()
