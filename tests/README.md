# Test Suite Documentation

This directory contains comprehensive test coverage for the Canvas Assignment Discord Bot.

## Test Structure

### Unit Tests (`tests/unit/`)
Unit tests focus on testing individual components in isolation with mocked dependencies.

- **`test_datetime_utils.py`** - Tests for datetime parsing, formatting, and timezone handling
- **`test_bot_helpers.py`** - Tests for bot helper functions and constants
- **`test_canvas_client.py`** - Tests for HTTP client functionality, pagination, and error handling
- **`test_canvas_endpoints.py`** - Tests for Canvas API endpoint wrappers
- **`test_config.py`** - Tests for configuration loading from environment variables

### Integration Tests (`tests/integration/`)
Integration tests verify that multiple components work together correctly.

- **`test_canvas_integration.py`** - Tests Canvas API client and endpoints working together
- **`test_database_integration.py`** - Tests complex database workflows and multi-table operations
- **`test_sync_integration.py`** - Tests Canvas data synchronization from API to database
- **`test_datetime_integration.py`** - Tests datetime utilities in realistic Canvas workflows

## Running Tests

### Run All Tests
```powershell
& "C:/Workspace/ASE 420/assignment-discord-bot/.venv/Scripts/python.exe" -m unittest discover -s tests -p "test_*.py" -v
```

### Run Unit Tests Only
```powershell
& "C:/Workspace/ASE 420/assignment-discord-bot/.venv/Scripts/python.exe" -m unittest discover -s tests/unit -p "test_*.py" -v
```

### Run Integration Tests Only
```powershell
& "C:/Workspace/ASE 420/assignment-discord-bot/.venv/Scripts/python.exe" -m unittest discover -s tests/integration -p "test_*.py" -v
```

### Run Specific Test File
```powershell
& "C:/Workspace/ASE 420/assignment-discord-bot/.venv/Scripts/python.exe" -m unittest tests.unit.test_datetime_utils -v
```

### Run Specific Test Class
```powershell
& "C:/Workspace/ASE 420/assignment-discord-bot/.venv/Scripts/python.exe" -m unittest tests.unit.test_datetime_utils.TestDatetimeUtils -v
```

### Run Specific Test Method
```powershell
& "C:/Workspace/ASE 420/assignment-discord-bot/.venv/Scripts/python.exe" -m unittest tests.unit.test_datetime_utils.TestDatetimeUtils.test_parse_canvas_datetime_with_z -v
```

## Test Coverage

### Unit Tests (44 tests)
- ✅ Datetime utilities: 13 tests
- ✅ Bot helpers: 10 tests
- ✅ Canvas client: 9 tests
- ✅ Canvas endpoints: 7 tests
- ✅ Configuration: 3 tests
- ⏭️ 1 skipped (environment variable isolation)

### Integration Tests
- ✅ Canvas API integration: 6 tests
- ✅ Database workflows: 6 tests
- ✅ Sync operations: 4 tests
- ✅ Datetime workflows: 9 tests

## Test Database

Integration tests use a separate test database (`data/test_canvas_bot.db` and variants) that is created fresh for each test and cleaned up afterward. This ensures tests don't interfere with production data or each other.

## Test Isolation

- **Unit tests**: Use mocking to isolate components and avoid external dependencies
- **Integration tests**: Use `IsolatedAsyncioTestCase` for async tests with proper setup/teardown
- **Database tests**: Create temporary test databases that are deleted after each test

## Adding New Tests

### Unit Test Template
```python
import unittest
from unittest.mock import Mock, patch

class TestYourComponent(unittest.TestCase):
    def setUp(self):
        # Setup test fixtures
        pass
    
    def test_your_feature(self):
        # Arrange
        # Act
        # Assert
        pass
```

### Integration Test Template
```python
import unittest

class TestYourIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Setup test environment
        pass
    
    async def asyncTearDown(self):
        # Cleanup
        pass
    
    async def test_your_workflow(self):
        # Arrange
        # Act
        # Assert
        pass
```

## Best Practices

1. **Unit Tests**: Mock all external dependencies (API calls, database, file system)
2. **Integration Tests**: Use real implementations but isolated test data
3. **Naming**: Use descriptive test names that explain what is being tested
4. **Assertions**: Include meaningful assertion messages
5. **Cleanup**: Always clean up test data and resources
6. **Independence**: Tests should not depend on each other
7. **Documentation**: Add docstrings explaining what each test verifies
