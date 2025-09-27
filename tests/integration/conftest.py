"""
Pytest configuration for integration tests.
Provides fixtures and setup for integration testing.
"""
import pytest
import os
from django.test import TransactionTestCase
from django.core.management import call_command
from django.db import transaction
from rest_framework.test import APIClient

from factories import (
    RoleFactory, PolinizadorUserFactory, GerminadorUserFactory,
    SecretariaUserFactory, AdministradorUserFactory,
    PollinationTypeFactory, AlertTypeFactory, ReportTypeFactory
)


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup test database with required data."""
    with django_db_blocker.unblock():
        # Create essential data that all tests need
        setup_test_data()


def setup_test_data():
    """Create essential test data."""
    # Create roles
    roles = ['Polinizador', 'Germinador', 'Secretaria', 'Administrador']
    for role_name in roles:
        RoleFactory(name=role_name)
    
    # Create pollination types
    poll_types = ['Self', 'Sibling', 'Híbrido']
    for poll_type in poll_types:
        PollinationTypeFactory(name=poll_type)
    
    # Create alert types
    alert_types = ['semanal', 'preventiva', 'frecuente']
    for alert_type in alert_types:
        AlertTypeFactory(name=alert_type)
    
    # Create report types
    report_types = ['pollination', 'germination', 'statistical']
    for report_type in report_types:
        ReportTypeFactory(name=report_type)


@pytest.fixture
def api_client():
    """Provide API client for testing."""
    return APIClient()


@pytest.fixture
def authenticated_polinizador_client():
    """Provide authenticated API client for polinizador."""
    user = PolinizadorUserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def authenticated_germinador_client():
    """Provide authenticated API client for germinador."""
    user = GerminadorUserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def authenticated_admin_client():
    """Provide authenticated API client for admin."""
    user = AdministradorUserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def test_users():
    """Provide test users with different roles."""
    return {
        'polinizador': PolinizadorUserFactory(),
        'germinador': GerminadorUserFactory(),
        'secretaria': SecretariaUserFactory(),
        'admin': AdministradorUserFactory()
    }


@pytest.fixture
def clean_database():
    """Ensure clean database state for each test."""
    # This fixture can be used to clean up data between tests
    yield
    # Cleanup code would go here if needed


class IntegrationTestMixin:
    """Mixin class for integration tests with common utilities."""
    
    def assert_api_response(self, response, expected_status, expected_keys=None):
        """Assert API response status and structure."""
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.data}"
        
        if expected_keys and response.status_code < 400:
            for key in expected_keys:
                assert key in response.data, f"Key '{key}' not found in response data"
    
    def assert_permission_denied(self, response):
        """Assert that permission was denied."""
        assert response.status_code in [403, 401], f"Expected 401 or 403, got {response.status_code}"
    
    def assert_not_found(self, response):
        """Assert that resource was not found."""
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def assert_validation_error(self, response, field_name=None):
        """Assert that validation error occurred."""
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        if field_name:
            assert field_name in str(response.data), f"Field '{field_name}' not found in validation errors"


# Pytest markers for categorizing tests
pytest.mark.integration = pytest.mark.integration
pytest.mark.workflow = pytest.mark.workflow
pytest.mark.security = pytest.mark.security
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow


# Custom pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "workflow: mark test as workflow test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add integration marker to all tests in integration directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add workflow marker to workflow tests
        if "workflow" in item.name:
            item.add_marker(pytest.mark.workflow)
        
        # Add security marker to security tests
        if any(keyword in item.name for keyword in ["security", "permission", "auth"]):
            item.add_marker(pytest.mark.security)
        
        # Add performance marker to performance tests
        if any(keyword in item.name for keyword in ["performance", "large_dataset", "bulk"]):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)


# Database transaction handling for integration tests
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass


@pytest.fixture
def transactional_db(db):
    """Provide transactional database access."""
    with transaction.atomic():
        yield


# Environment setup
@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Setup test environment."""
    # Set test environment variables
    os.environ['DJANGO_SETTINGS_MODULE'] = 'sistema_polinizacion.settings.test_settings'
    os.environ['TESTING'] = 'True'
    
    yield
    
    # Cleanup
    if 'TESTING' in os.environ:
        del os.environ['TESTING']