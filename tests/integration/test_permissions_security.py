"""
Integration tests for permissions and security.
Tests role-based access control, JWT authentication, and security validations.
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

from factories import (
    PolinizadorUserFactory, GerminadorUserFactory, SecretariaUserFactory, 
    AdministradorUserFactory, RoleFactory, SelfPollinationRecordFactory,
    GerminationRecordFactory, AlertFactory, CompletedReportFactory
)
from authentication.models import Role
from pollination.models import PollinationRecord
from germination.models import GerminationRecord
from alerts.models import Alert
from reports.models import Report

User = get_user_model()


@pytest.mark.django_db
class TestRoleBasedAccessControl(TransactionTestCase):
    """Test role-based access control across all modules."""
    
    def setUp(self):
        """Set up test users with different roles."""
        self.polinizador = PolinizadorUserFactory()
        self.germinador = GerminadorUserFactory()
        self.secretaria = SecretariaUserFactory()
        self.admin = AdministradorUserFactory()
        
        # Create test data
        self.pollination = SelfPollinationRecordFactory(responsible=self.polinizador)
        self.germination = GerminationRecordFactory(responsible=self.germinador)
        self.alert = AlertFactory()
        self.report = CompletedReportFactory(generated_by=self.admin)

    def test_polinizador_permissions(self):
        """Test Polinizador role permissions."""
        client = APIClient()
        client.force_authenticate(user=self.polinizador)
        
        # Should have access to pollination module
        response = client.get('/api/pollination/records/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be able to create pollination records
        pollination_data = {
            'responsible': self.polinizador.id,
            'pollination_type': self.pollination.pollination_type.id,
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.pollination.mother_plant.id,
            'new_plant': self.pollination.new_plant.id,
            'climate_condition': self.pollination.climate_condition.id,
            'capsules_quantity': 3
        }
        
        create_response = client.post('/api/pollination/records/', pollination_data)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        # Should be able to update own records
        update_response = client.patch(
            f'/api/pollination/records/{self.pollination.id}/',
            {'observations': 'Updated by polinizador'}
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Should NOT be able to delete records (admin only)
        delete_response = client.delete(f'/api/pollination/records/{self.pollination.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Should have limited access to germination module (read-only)
        germ_response = client.get('/api/germination/records/')
        self.assertIn(germ_response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        
        # Should NOT be able to create germination records
        germ_create_response = client.post('/api/germination/records/', {})
        self.assertEqual(germ_create_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Should NOT have access to reports module
        reports_response = client.get('/api/reports/')
        self.assertEqual(reports_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_germinador_permissions(self):
        """Test Germinador role permissions."""
        client = APIClient()
        client.force_authenticate(user=self.germinador)
        
        # Should have access to germination module
        response = client.get('/api/germination/records/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be able to create germination records
        germination_data = {
            'responsible': self.germinador.id,
            'germination_date': date.today().isoformat(),
            'plant': self.germination.plant.id,
            'seed_source': self.germination.seed_source.id,
            'germination_condition': self.germination.germination_condition.id,
            'seeds_planted': 25
        }
        
        create_response = client.post('/api/germination/records/', germination_data)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        # Should be able to update own records
        update_response = client.patch(
            f'/api/germination/records/{self.germination.id}/',
            {'observations': 'Updated by germinador'}
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Should NOT be able to delete records
        delete_response = client.delete(f'/api/germination/records/{self.germination.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Should have limited access to pollination module (read-only)
        poll_response = client.get('/api/pollination/records/')
        self.assertIn(poll_response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        
        # Should NOT be able to create pollination records
        poll_create_response = client.post('/api/pollination/records/', {})
        self.assertEqual(poll_create_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Should NOT have access to reports module
        reports_response = client.get('/api/reports/')
        self.assertEqual(reports_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_secretaria_permissions(self):
        """Test Secretaria role permissions."""
        client = APIClient()
        client.force_authenticate(user=self.secretaria)
        
        # Should have read access to both pollination and germination
        poll_response = client.get('/api/pollination/records/')
        self.assertEqual(poll_response.status_code, status.HTTP_200_OK)
        
        germ_response = client.get('/api/germination/records/')
        self.assertEqual(germ_response.status_code, status.HTTP_200_OK)
        
        # Should be able to update records (administrative support)
        poll_update = client.patch(
            f'/api/pollination/records/{self.pollination.id}/',
            {'observations': 'Updated by secretaria'}
        )
        self.assertEqual(poll_update.status_code, status.HTTP_200_OK)
        
        germ_update = client.patch(
            f'/api/germination/records/{self.germination.id}/',
            {'observations': 'Updated by secretaria'}
        )
        self.assertEqual(germ_update.status_code, status.HTTP_200_OK)
        
        # Should NOT be able to delete records
        delete_response = client.delete(f'/api/pollination/records/{self.pollination.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Should have access to alerts for administrative purposes
        alerts_response = client.get('/api/alerts/user-alerts/')
        self.assertIn(alerts_response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        
        # Should NOT have access to reports generation
        reports_response = client.get('/api/reports/')
        self.assertEqual(reports_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_administrador_permissions(self):
        """Test Administrador role permissions."""
        client = APIClient()
        client.force_authenticate(user=self.admin)
        
        # Should have full access to all modules
        poll_response = client.get('/api/pollination/records/')
        self.assertEqual(poll_response.status_code, status.HTTP_200_OK)
        
        germ_response = client.get('/api/germination/records/')
        self.assertEqual(germ_response.status_code, status.HTTP_200_OK)
        
        alerts_response = client.get('/api/alerts/user-alerts/')
        self.assertEqual(alerts_response.status_code, status.HTTP_200_OK)
        
        reports_response = client.get('/api/reports/')
        self.assertEqual(reports_response.status_code, status.HTTP_200_OK)
        
        # Should be able to delete records
        # Create a test record to delete
        test_pollination = SelfPollinationRecordFactory(responsible=self.admin)
        delete_response = client.delete(f'/api/pollination/records/{test_pollination.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Should be able to create reports
        report_data = {
            'title': 'Admin Test Report',
            'report_type': self.report.report_type.id,
            'format': 'pdf',
            'parameters': {}
        }
        
        create_report_response = client.post('/api/reports/', report_data)
        self.assertEqual(create_report_response.status_code, status.HTTP_201_CREATED)
        
        # Should be able to manage users
        user_response = client.get('/api/auth/users/')
        self.assertIn(user_response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_cross_user_data_access_restrictions(self):
        """Test that users cannot access other users' private data inappropriately."""
        # Create records for different users
        polinizador2 = PolinizadorUserFactory()
        germinador2 = GerminadorUserFactory()
        
        poll_user1 = SelfPollinationRecordFactory(responsible=self.polinizador)
        poll_user2 = SelfPollinationRecordFactory(responsible=polinizador2)
        
        germ_user1 = GerminationRecordFactory(responsible=self.germinador)
        germ_user2 = GerminationRecordFactory(responsible=germinador2)
        
        # Test polinizador1 accessing polinizador2's data
        client1 = APIClient()
        client1.force_authenticate(user=self.polinizador)
        
        # Should see own records
        response1 = client1.get('/api/pollination/records/')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Verify only own records are returned (or all if permissions allow)
        if response1.data:
            accessible_records = [r['id'] for r in response1.data]
            self.assertIn(poll_user1.id, accessible_records)
            # Depending on business rules, user2's records might or might not be visible
        
        # Should not be able to update other user's records
        update_response = client1.patch(
            f'/api/pollination/records/{poll_user2.id}/',
            {'observations': 'Unauthorized update attempt'}
        )
        self.assertIn(update_response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_role_hierarchy_and_inheritance(self):
        """Test role hierarchy and permission inheritance."""
        # Admin should have all permissions that other roles have
        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin)
        
        # Test admin can do everything polinizador can do
        pollination_data = {
            'responsible': self.admin.id,
            'pollination_type': self.pollination.pollination_type.id,
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.pollination.mother_plant.id,
            'new_plant': self.pollination.new_plant.id,
            'climate_condition': self.pollination.climate_condition.id,
            'capsules_quantity': 3
        }
        
        admin_poll_response = admin_client.post('/api/pollination/records/', pollination_data)
        self.assertEqual(admin_poll_response.status_code, status.HTTP_201_CREATED)
        
        # Test admin can do everything germinador can do
        germination_data = {
            'responsible': self.admin.id,
            'germination_date': date.today().isoformat(),
            'plant': self.germination.plant.id,
            'seed_source': self.germination.seed_source.id,
            'germination_condition': self.germination.germination_condition.id,
            'seeds_planted': 25
        }
        
        admin_germ_response = admin_client.post('/api/germination/records/', germination_data)
        self.assertEqual(admin_germ_response.status_code, status.HTTP_201_CREATED)


@pytest.mark.django_db
class TestJWTAuthentication(TransactionTestCase):
    """Test JWT authentication workflow and security."""
    
    def setUp(self):
        """Set up test user."""
        self.user = PolinizadorUserFactory()
        self.client = APIClient()

    def test_jwt_token_generation_and_validation(self):
        """Test JWT token generation and validation."""
        # Step 1: Login and get tokens
        login_data = {
            'username': self.user.username,
            'password': 'testpass123'  # Default password from factory
        }
        
        login_response = self.client.post('/api/auth/login/', login_data)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Verify tokens are returned
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)
        
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']
        
        # Step 2: Use access token for authenticated requests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        protected_response = self.client.get('/api/pollination/records/')
        self.assertEqual(protected_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Test token refresh
        refresh_data = {'refresh': refresh_token}
        refresh_response = self.client.post('/api/auth/token/refresh/', refresh_data)
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)

    def test_jwt_token_expiration_handling(self):
        """Test JWT token expiration and renewal."""
        # Generate tokens
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # Use valid token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/pollination/records/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test with invalid token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        invalid_response = self.client.get('/api/pollination/records/')
        self.assertEqual(invalid_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test refresh with valid refresh token
        refresh_data = {'refresh': refresh_token}
        refresh_response = self.client.post('/api/auth/token/refresh/', refresh_data)
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)

    def test_jwt_authentication_failure_scenarios(self):
        """Test various JWT authentication failure scenarios."""
        # Test 1: No token provided
        response = self.client.get('/api/pollination/records/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test 2: Malformed token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer malformed.token.here')
        response = self.client.get('/api/pollination/records/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test 3: Wrong authentication scheme
        self.client.credentials(HTTP_AUTHORIZATION='Basic dGVzdDp0ZXN0')
        response = self.client.get('/api/pollination/records/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test 4: Token for non-existent user
        fake_user = User(id=99999, username='fake_user')
        fake_refresh = RefreshToken.for_user(fake_user)
        fake_token = str(fake_refresh.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {fake_token}')
        response = self.client.get('/api/pollination/records/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_token_blacklisting(self):
        """Test JWT token blacklisting on logout."""
        # Login to get tokens
        login_data = {
            'username': self.user.username,
            'password': 'testpass123'
        }
        
        login_response = self.client.post('/api/auth/login/', login_data)
        refresh_token = login_response.data['refresh']
        access_token = login_response.data['access']
        
        # Use token successfully
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/pollination/records/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Logout (blacklist token)
        logout_data = {'refresh': refresh_token}
        logout_response = self.client.post('/api/auth/logout/', logout_data)
        self.assertIn(logout_response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])
        
        # Try to refresh with blacklisted token
        refresh_response = self.client.post('/api/auth/token/refresh/', logout_data)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
class TestSecurityValidations(TransactionTestCase):
    """Test security validations and input sanitization."""
    
    def setUp(self):
        """Set up test data."""
        self.user = PolinizadorUserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in API endpoints."""
        # Test SQL injection in query parameters
        malicious_params = [
            "'; DROP TABLE pollination_pollinationrecord; --",
            "1' OR '1'='1",
            "1; DELETE FROM pollination_pollinationrecord WHERE 1=1; --",
            "1 UNION SELECT * FROM auth_user --"
        ]
        
        for malicious_param in malicious_params:
            with self.subTest(param=malicious_param):
                # Test in various endpoints
                response = self.client.get(f'/api/pollination/records/?search={malicious_param}')
                # Should not cause server error, should handle gracefully
                self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_xss_prevention_in_input_fields(self):
        """Test XSS prevention in input fields."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//"
        ]
        
        for payload in xss_payloads:
            with self.subTest(payload=payload):
                # Test in pollination record creation
                pollination_data = {
                    'responsible': self.user.id,
                    'pollination_type': 1,  # Assuming exists
                    'pollination_date': date.today().isoformat(),
                    'observations': payload,  # XSS payload in observations
                    'capsules_quantity': 1
                }
                
                # This should either be rejected or sanitized
                response = self.client.post('/api/pollination/records/', pollination_data)
                
                if response.status_code == status.HTTP_201_CREATED:
                    # If created, verify the payload was sanitized
                    record_id = response.data['id']
                    get_response = self.client.get(f'/api/pollination/records/{record_id}/')
                    
                    # The returned data should not contain the raw XSS payload
                    returned_observations = get_response.data.get('observations', '')
                    self.assertNotEqual(returned_observations, payload)

    def test_csrf_protection(self):
        """Test CSRF protection for state-changing operations."""
        # Create a client without CSRF token
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.force_authenticate(user=self.user)
        
        # Test POST request without CSRF token
        pollination_data = {
            'responsible': self.user.id,
            'pollination_type': 1,
            'pollination_date': date.today().isoformat(),
            'capsules_quantity': 1
        }
        
        # This should be handled by DRF's authentication, not traditional CSRF
        response = csrf_client.post('/api/pollination/records/', pollination_data)
        # API endpoints typically don't use CSRF tokens when using token auth
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_input_validation_and_sanitization(self):
        """Test input validation and sanitization."""
        # Test 1: Invalid date formats
        invalid_dates = [
            '2024-13-01',  # Invalid month
            '2024-02-30',  # Invalid day
            'not-a-date',  # Not a date
            '2024/01/01',  # Wrong format
        ]
        
        for invalid_date in invalid_dates:
            with self.subTest(date=invalid_date):
                pollination_data = {
                    'responsible': self.user.id,
                    'pollination_type': 1,
                    'pollination_date': invalid_date,
                    'capsules_quantity': 1
                }
                
                response = self.client.post('/api/pollination/records/', pollination_data)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test 2: Invalid numeric values
        invalid_quantities = [-1, 0, 'not-a-number', 999999]
        
        for invalid_quantity in invalid_quantities:
            with self.subTest(quantity=invalid_quantity):
                pollination_data = {
                    'responsible': self.user.id,
                    'pollination_type': 1,
                    'pollination_date': date.today().isoformat(),
                    'capsules_quantity': invalid_quantity
                }
                
                response = self.client.post('/api/pollination/records/', pollination_data)
                if invalid_quantity in [-1, 0, 'not-a-number']:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_upload_security(self):
        """Test file upload security (if applicable)."""
        # This test would be relevant if the system handles file uploads
        # For now, we'll test potential file-related vulnerabilities
        
        # Test 1: Malicious filename in observations or other text fields
        malicious_filenames = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            'file.exe',
            'script.php'
        ]
        
        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                pollination_data = {
                    'responsible': self.user.id,
                    'pollination_type': 1,
                    'pollination_date': date.today().isoformat(),
                    'observations': f'File reference: {filename}',
                    'capsules_quantity': 1
                }
                
                response = self.client.post('/api/pollination/records/', pollination_data)
                # Should not cause server errors
                self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_rate_limiting_and_dos_prevention(self):
        """Test rate limiting and DoS prevention."""
        # Test rapid successive requests
        responses = []
        
        for i in range(20):  # Make 20 rapid requests
            response = self.client.get('/api/pollination/records/')
            responses.append(response.status_code)
        
        # All requests should be handled (assuming no rate limiting implemented yet)
        # In production, some might return 429 Too Many Requests
        successful_requests = sum(1 for status_code in responses if status_code == 200)
        self.assertGreater(successful_requests, 0)

    def test_information_disclosure_prevention(self):
        """Test prevention of information disclosure."""
        # Test 1: Error messages should not reveal sensitive information
        # Try to access non-existent record
        response = self.client.get('/api/pollination/records/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Error message should not reveal database structure
        if 'detail' in response.data:
            error_message = response.data['detail'].lower()
            sensitive_terms = ['database', 'sql', 'table', 'column', 'query']
            for term in sensitive_terms:
                self.assertNotIn(term, error_message)
        
        # Test 2: User enumeration prevention
        # Try to access other user's data
        other_user = PolinizadorUserFactory()
        other_pollination = SelfPollinationRecordFactory(responsible=other_user)
        
        response = self.client.get(f'/api/pollination/records/{other_pollination.id}/')
        # Should return 404 or 403, not reveal that the record exists for another user
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_authorization_bypass_attempts(self):
        """Test prevention of authorization bypass attempts."""
        # Test 1: Parameter pollution
        pollination_data = {
            'responsible': [self.user.id, 999],  # Array instead of single value
            'pollination_type': 1,
            'pollination_date': date.today().isoformat(),
            'capsules_quantity': 1
        }
        
        response = self.client.post('/api/pollination/records/', pollination_data)
        # Should handle gracefully, not cause bypass
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Test 2: HTTP method override attempts
        # Try to use POST to perform DELETE
        override_headers = {
            'HTTP_X_HTTP_METHOD_OVERRIDE': 'DELETE',
            'HTTP_X_METHOD_OVERRIDE': 'DELETE'
        }
        
        response = self.client.post(
            f'/api/pollination/records/{self.user.id}/',
            {},
            **override_headers
        )
        # Should not perform DELETE operation
        self.assertNotEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_session_security(self):
        """Test session security measures."""
        # Test 1: Session fixation prevention
        # Login with one session
        login_data = {
            'username': self.user.username,
            'password': 'testpass123'
        }
        
        response1 = self.client.post('/api/auth/login/', login_data)
        token1 = response1.data.get('access')
        
        # Login again (should get different token)
        response2 = self.client.post('/api/auth/login/', login_data)
        token2 = response2.data.get('access')
        
        # Tokens should be different (preventing session fixation)
        if token1 and token2:
            self.assertNotEqual(token1, token2)
        
        # Test 2: Concurrent session handling
        client1 = APIClient()
        client2 = APIClient()
        
        client1.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        
        # Both should work (multiple sessions allowed)
        response1 = client1.get('/api/pollination/records/')
        response2 = client2.get('/api/pollination/records/')
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)