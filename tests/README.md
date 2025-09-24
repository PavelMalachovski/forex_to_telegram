# Test Suite Documentation

This directory contains comprehensive tests for the modern FastAPI Forex Bot application, following Context7 best practices and modern testing patterns.

## 📁 Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and shared fixtures
├── test_runner.py                 # Test runner script
├── README.md                      # This documentation
├── test_core/                     # Core module tests
│   ├── test_config.py            # Configuration tests
│   └── test_exceptions.py        # Exception handling tests
├── test_models/                   # Data model tests
│   └── test_user.py              # User model tests
├── test_services/                 # Service layer tests
│   └── test_user_service.py      # User service tests
├── test_api/                      # API endpoint tests
│   └── test_users.py             # User API tests
├── test_integration/              # Integration tests
│   └── test_telegram_webhook.py  # Telegram webhook integration
├── test_performance/              # Performance tests
│   └── test_api_performance.py  # API performance tests
└── [legacy tests]                 # Original tests (to be migrated)
```

## 🧪 Test Categories

### 1. Unit Tests (`test_core/`, `test_models/`, `test_services/`)
- **Purpose**: Test individual components in isolation
- **Scope**: Functions, classes, and methods
- **Dependencies**: Mocked external dependencies
- **Speed**: Fast execution (< 1 second per test)

### 2. Integration Tests (`test_integration/`)
- **Purpose**: Test component interactions
- **Scope**: API endpoints, database operations, external services
- **Dependencies**: Real database, mocked external APIs
- **Speed**: Medium execution (1-5 seconds per test)

### 3. Performance Tests (`test_performance/`)
- **Purpose**: Test performance characteristics
- **Scope**: Response times, memory usage, concurrent operations
- **Dependencies**: Real database and services
- **Speed**: Slow execution (5+ seconds per test)

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_core/          # Unit tests only
pytest tests/test_api/           # API tests only
pytest tests/test_integration/   # Integration tests only

# Run with coverage
pytest --cov=src --cov-report=html

# Run performance tests (exclude slow ones)
pytest tests/test_performance/ -m "not slow"
```

### Using the Test Runner
```bash
# Run comprehensive test suite
python tests/test_runner.py

# This will run:
# - Unit tests
# - API tests
# - Integration tests
# - Performance tests
# - Coverage report
# - Linting
# - Type checking
```

### Test Markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"

# Run async tests only
pytest -m asyncio
```

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
- **Async Mode**: Automatic async test detection
- **Markers**: Organized test categorization
- **Output**: Verbose output with short tracebacks
- **Logging**: Structured logging for debugging
- **Coverage**: HTML and terminal coverage reports

### Test Fixtures (`conftest.py`)
- **Database**: In-memory SQLite for testing
- **Client**: Async HTTP client for API testing
- **Sample Data**: Predefined test data fixtures
- **Mocks**: External service mocks

## 📊 Test Coverage

The test suite aims for comprehensive coverage:

- **Models**: 100% coverage of Pydantic models
- **Services**: 90%+ coverage of business logic
- **API Endpoints**: 95%+ coverage of REST endpoints
- **Core Components**: 100% coverage of configuration and exceptions

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage in terminal
pytest --cov=src --cov-report=term-missing

# Coverage threshold enforcement
pytest --cov=src --cov-fail-under=80
```

## 🎯 Test Patterns

### Async Testing
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Database Testing
```python
async def test_database_operation(test_db_session: AsyncSession):
    # Test database operations
    user = await create_user(test_db_session, user_data)
    assert user.id is not None
```

### API Testing
```python
async def test_api_endpoint(test_client: AsyncClient):
    response = await test_client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
```

### Mocking External Services
```python
async def test_external_service(mock_external_api):
    mock_external_api.get.return_value = mock_response
    result = await service.call_external_api()
    assert result is not None
```

## 🔍 Test Data Management

### Sample Data Fixtures
- **`sample_user_data`**: Complete user data for testing
- **`sample_forex_news_data`**: Forex news data
- **`sample_chart_request_data`**: Chart generation requests
- **`sample_notification_data`**: Notification data
- **`sample_telegram_update_data`**: Telegram webhook updates

### Database State Management
- **Isolation**: Each test gets a clean database
- **Transactions**: Automatic rollback after each test
- **Fixtures**: Reusable test data setup

## 🚨 Error Handling Tests

### Exception Testing
```python
def test_exception_handling():
    with pytest.raises(ValidationError) as exc_info:
        invalid_operation()
    assert "expected error message" in str(exc_info.value)
```

### API Error Testing
```python
async def test_api_error_response(test_client: AsyncClient):
    response = await test_client.get("/api/v1/users/999999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
```

## 📈 Performance Testing

### Response Time Testing
```python
async def test_response_time(test_client: AsyncClient):
    start_time = time.time()
    response = await test_client.get("/api/v1/users/")
    end_time = time.time()

    assert response.status_code == 200
    assert (end_time - start_time) < 1.0  # Under 1 second
```

### Concurrent Testing
```python
async def test_concurrent_requests(test_client: AsyncClient):
    tasks = [test_client.get("/api/v1/users/") for _ in range(10)]
    responses = await asyncio.gather(*tasks)

    for response in responses:
        assert response.status_code == 200
```

## 🛠️ Debugging Tests

### Verbose Output
```bash
# Run with maximum verbosity
pytest -vvv

# Show print statements
pytest -s

# Show local variables on failure
pytest --tb=long
```

### Test Debugging
```python
# Add breakpoints in tests
import pdb; pdb.set_trace()

# Use pytest's built-in debugging
pytest --pdb
```

## 📋 Test Checklist

### Before Committing
- [ ] All tests pass (`pytest`)
- [ ] Coverage meets threshold (`pytest --cov=src --cov-fail-under=80`)
- [ ] No linting errors (`flake8 src/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Performance tests pass (`pytest tests/test_performance/ -m "not slow"`)

### Test Quality
- [ ] Tests are isolated and independent
- [ ] Tests use descriptive names
- [ ] Tests cover edge cases
- [ ] Tests use appropriate fixtures
- [ ] Tests have proper assertions
- [ ] Tests clean up after themselves

## 🔄 Continuous Integration

### GitHub Actions Integration
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 📚 Best Practices

### Test Organization
1. **One test file per module**
2. **Descriptive test names**
3. **Arrange-Act-Assert pattern**
4. **Minimal test data**
5. **Clear assertions**

### Async Testing
1. **Use `@pytest.mark.asyncio`**
2. **Proper async/await usage**
3. **Async fixtures for async resources**
4. **Concurrent testing for performance**

### Database Testing
1. **Use in-memory databases**
2. **Clean state for each test**
3. **Transaction rollback**
4. **Realistic test data**

### API Testing
1. **Test all HTTP methods**
2. **Test error responses**
3. **Test authentication**
4. **Test rate limiting**

## 🎉 Conclusion

This comprehensive test suite ensures the reliability, performance, and maintainability of the Forex Bot application. The tests follow modern best practices and provide excellent coverage of all application components.

For questions or contributions to the test suite, please refer to the main project documentation or create an issue in the repository.
