# Integration Tests - Sistema de Polinización y Germinación

This directory contains comprehensive integration tests for the Sistema de Polinización y Germinación. These tests verify complete workflows, end-to-end functionality, permissions, and security measures.

## Test Structure

### Test Modules

1. **`test_pollination_workflow.py`** - Complete pollination workflow tests
   - Self, Sibling, and Hybrid pollination workflows
   - Business logic validation
   - Alert generation integration
   - Multi-user scenarios
   - Error handling

2. **`test_germination_workflow.py`** - Complete germination workflow tests
   - Internal and external seed source workflows
   - Different environmental conditions
   - Success rate tracking
   - Cross-module integration with pollination
   - Alert timing and generation

3. **`test_alerts_workflow.py`** - Automatic alert generation workflow tests
   - Weekly, preventive, and frequent alerts
   - Notification delivery
   - Celery task integration
   - User interactions (read, dismiss)
   - Bulk operations and filtering

4. **`test_reports_workflow.py`** - Complete reports generation workflow tests
   - Pollination, germination, and statistical reports
   - Multiple export formats (PDF, Excel, JSON)
   - Large dataset performance
   - Scheduled generation
   - Access control

5. **`test_permissions_security.py`** - Role-based access control and security tests
   - Role-specific permissions (Polinizador, Germinador, Secretaria, Administrador)
   - Cross-user data access restrictions
   - SQL injection prevention
   - XSS prevention
   - Input validation and sanitization

6. **`test_authentication_integration.py`** - Authentication system integration tests
   - Complete login/logout workflows
   - JWT token management
   - Password change workflows
   - Role assignment and permissions
   - User profile management
   - Concurrent sessions

### Supporting Files

- **`conftest.py`** - Pytest configuration and fixtures
- **`test_runner.py`** - Custom test runner with coverage reporting
- **`README.md`** - This documentation file

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-django pytest-cov factory-boy

# Ensure test database is configured
python manage.py migrate --settings=sistema_polinizacion.settings.test_settings
```

### Run All Integration Tests

```bash
# Using the custom test runner
python tests/integration/test_runner.py all

# Using Django's test runner
python manage.py test tests.integration --verbosity=2

# Using pytest
pytest tests/integration/ -v
```

### Run Specific Test Categories

```bash
# Run specific workflow tests
python tests/integration/test_runner.py pollination
python tests/integration/test_runner.py germination
python tests/integration/test_runner.py alerts
python tests/integration/test_runner.py reports

# Run security tests
python tests/integration/test_runner.py security

# Run performance tests
python tests/integration/test_runner.py performance
```

### Run with Coverage

```bash
# Using the test runner (includes coverage)
python tests/integration/test_runner.py all

# Using pytest with coverage
pytest tests/integration/ --cov=. --cov-report=html --cov-report=term
```

### Run Specific Test Classes or Methods

```bash
# Run specific test class
python manage.py test tests.integration.test_pollination_workflow.TestPollinationWorkflowIntegration

# Run specific test method
python manage.py test tests.integration.test_pollination_workflow.TestPollinationWorkflowIntegration.test_complete_self_pollination_workflow
```

## Test Categories and Markers

Tests are categorized using pytest markers:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.workflow` - Workflow-specific tests
- `@pytest.mark.security` - Security and permissions tests
- `@pytest.mark.performance` - Performance-focused tests
- `@pytest.mark.slow` - Tests that take longer to run

### Run Tests by Marker

```bash
# Run only security tests
pytest tests/integration/ -m security

# Run only workflow tests
pytest tests/integration/ -m workflow

# Skip slow tests
pytest tests/integration/ -m "not slow"
```

## Test Data and Factories

Integration tests use Factory Boy factories for creating test data:

- **Authentication Factories**: Users with different roles
- **Pollination Factories**: Plants, pollination records, climate conditions
- **Germination Factories**: Seed sources, germination records, conditions
- **Alerts Factories**: Alert types, alerts, user alerts
- **Reports Factories**: Report types, completed reports

### Example Factory Usage

```python
from factories import PolinizadorUserFactory, SelfPollinationRecordFactory

# Create test user
user = PolinizadorUserFactory()

# Create pollination record
pollination = SelfPollinationRecordFactory(responsible=user)
```

## Test Scenarios Covered

### Pollination Workflow Tests
- ✅ Complete self pollination workflow (creation → alerts → updates)
- ✅ Complete sibling pollination workflow with validation
- ✅ Complete hybrid pollination workflow
- ✅ Business logic validation (date validation, duplicates)
- ✅ Multi-user scenarios and permissions
- ✅ Error handling and edge cases

### Germination Workflow Tests
- ✅ Germination from internal seed sources (pollination records)
- ✅ Germination from external seed sources
- ✅ Different environmental conditions testing
- ✅ Success rate tracking and calculations
- ✅ Cross-module integration with pollination
- ✅ Alert timing and generation

### Alerts Workflow Tests
- ✅ Automatic alert generation for pollination and germination
- ✅ Weekly, preventive, and frequent alert types
- ✅ Notification delivery and user interactions
- ✅ Bulk operations (mark as read, dismiss)
- ✅ Filtering and pagination
- ✅ Performance with large datasets

### Reports Workflow Tests
- ✅ Pollination report generation and export
- ✅ Germination report generation and export
- ✅ Statistical report generation with trends
- ✅ Multiple export formats (PDF, Excel, JSON)
- ✅ Large dataset performance testing
- ✅ Access control and permissions

### Security and Permissions Tests
- ✅ Role-based access control for all modules
- ✅ Cross-user data access restrictions
- ✅ JWT authentication and token management
- ✅ SQL injection prevention
- ✅ XSS prevention and input sanitization
- ✅ Authorization bypass prevention
- ✅ Session security measures

### Authentication Integration Tests
- ✅ Complete user registration workflow
- ✅ Login/logout workflows with JWT
- ✅ Password change workflows
- ✅ Role assignment and permission changes
- ✅ User profile management
- ✅ Concurrent session handling
- ✅ Error handling scenarios

## Performance Considerations

### Large Dataset Tests
- Tests with 100+ pollination records
- Tests with 100+ germination records
- Bulk alert generation and processing
- Report generation performance monitoring

### Performance Thresholds
- Alert generation: < 10 seconds for 80 records
- API responses: < 2 seconds for user alerts
- Report generation: < 30 seconds for large datasets

## Security Test Coverage

### Authentication Security
- JWT token validation and expiration
- Token blacklisting on logout
- Concurrent session management
- Password complexity validation

### Authorization Security
- Role-based access control
- Cross-user data access prevention
- Permission inheritance testing
- Authorization bypass prevention

### Input Security
- SQL injection prevention
- XSS prevention and sanitization
- CSRF protection (where applicable)
- File upload security (if applicable)

### Information Security
- Error message information disclosure prevention
- User enumeration prevention
- Sensitive data exposure prevention

## Continuous Integration

### Test Execution in CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  run: |
    python tests/integration/test_runner.py all
    
- name: Run Security Tests
  run: |
    python tests/integration/test_runner.py security
```

### Coverage Requirements
- Overall coverage: 85%+
- Security tests: 90%+
- Workflow tests: 90%+

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Ensure test database is configured
   python manage.py migrate --settings=sistema_polinizacion.settings.test_settings
   ```

2. **Factory Dependency Issues**
   ```bash
   # Install factory-boy
   pip install factory-boy
   ```

3. **Permission Errors**
   ```bash
   # Ensure roles are created in test setup
   python manage.py loaddata fixtures/initial_data.json --settings=sistema_polinizacion.settings.test_settings
   ```

4. **Celery Task Issues**
   ```bash
   # For tests that use Celery, ensure Redis/RabbitMQ is available or mock the tasks
   ```

### Debug Mode

Run tests with debug output:

```bash
# Verbose output
python manage.py test tests.integration --verbosity=3

# With pdb debugging
pytest tests/integration/ --pdb

# With print statements
pytest tests/integration/ -s
```

## Contributing

When adding new integration tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate factories for test data creation
3. Add proper test markers (`@pytest.mark.integration`, etc.)
4. Include both positive and negative test cases
5. Test error handling and edge cases
6. Update this README if adding new test categories

### Test Naming Convention

- Test classes: `Test{Module}WorkflowIntegration`
- Test methods: `test_{workflow_description}`
- Use descriptive names that explain what is being tested

### Example Test Structure

```python
@pytest.mark.django_db
class TestNewWorkflowIntegration(TransactionTestCase):
    """Test complete new workflow integration."""
    
    def setUp(self):
        """Set up test data."""
        # Setup code here
        
    def test_complete_workflow_success_case(self):
        """Test successful workflow execution."""
        # Test implementation
        
    def test_workflow_error_handling(self):
        """Test workflow error handling."""
        # Error case testing
```

## Test Results and Reporting

The test runner generates:
- Console output with test results
- Coverage reports (HTML and terminal)
- Performance metrics for slow tests
- Security test results summary

Coverage reports are generated in the `htmlcov/` directory and can be viewed in a web browser.