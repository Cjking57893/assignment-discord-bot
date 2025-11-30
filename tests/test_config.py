"""
Unit tests for config module.
Tests environment variable loading and configuration.
"""

import unittest
import os
from unittest.mock import patch


class TestConfig(unittest.TestCase):
    """Test suite for configuration loading."""

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_bot_token_12345',
        'CANVAS_TOKEN': 'test_canvas_token_67890',
        'CHANNEL_ID': '123456789',
        'CANVAS_BASE_URL': 'https://test.canvas.com/api/v1'
    })
    def test_config_loads_environment_variables(self):
        """Test that config module loads environment variables."""
        # Reload config module to pick up mocked env vars
        import importlib
        import config
        importlib.reload(config)
        
        self.assertEqual(config.BOT_TOKEN, 'test_bot_token_12345')
        self.assertEqual(config.CANVAS_TOKEN, 'test_canvas_token_67890')
        self.assertEqual(config.CHANNEL_ID, '123456789')
        self.assertEqual(config.CANVAS_BASE_URL, 'https://test.canvas.com/api/v1')

    @patch.dict(os.environ, {
        'BOT_TOKEN': 'test_token',
        'CANVAS_TOKEN': 'canvas_token'
    })
    def test_config_optional_variables(self):
        """Test that optional config variables can be None."""
        import importlib
        import config
        importlib.reload(config)
        
        # CHANNEL_ID is optional
        self.assertIsNotNone(config.BOT_TOKEN)
        self.assertIsNotNone(config.CANVAS_TOKEN)

    def test_headers_include_authorization(self):
        """Test that HEADERS include authorization token."""
        import config
        
        self.assertIn('Authorization', config.HEADERS)
        self.assertTrue(config.HEADERS['Authorization'].startswith('Bearer '))


if __name__ == "__main__":
    unittest.main()
