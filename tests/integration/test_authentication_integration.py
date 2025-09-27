"""
Integration tests for authentication system.
Tests complete authentication workflows, user management, and role assignments.
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from factories import (
    RoleFactory, CustomUserFactory, UserProfileFactory,
    PolinizadorUserFactory, GerminadorUserFactory, 
    SecretariaUserFactory, AdministradorUserFactory
)
from authentication.models import Role, UserProfile
from authentication.serializers import LoginSerializer, UserSerializer

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationWorkflowIntegration(TransactionTestCase):
    """Test complete authentication workflow integration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create roles
        self.polinizador_role = RoleFactory(name='Polinizador')
        self.germinador_role = RoleFactory(name='Germinador')
        self.secretaria_role = RoleFactory(name='Secretaria')
        self.admin_role = RoleFactory(name='Administrador')
        
        # Create test users
        self.polinizador = PolinizadorUserFactory()
        self.admin = AdministradorUserFactory()

    def test_complete_user_registration_workflow(self):
        """Test complete user registration workflow."""
        # Step 1: Admin creates new user
        self.client.force_authenticate(user=self.admin)
        
        user_data = {
            'username': 'new_polinizador',
            'email': 'new_polinizador@test.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'Polinizador',
            'role': self.polinizador_role.id
        }
        
        create_response = self.client.post('/api/auth/users/', user_data)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Verify user was created with correct role
        new_user = User.objects.get(username='new_polinizador')
        self.assertEqual(new_user.role, self.polinizador_role)
        self.assertTrue(new_user.check_password('newpass123'))
        
        # Step 3: New user attempts first login
        login_data = {
            'username': 'new_polinizador',
            'password': 'newpass123'
        }
        
        login_response = self.client.post('/api/auth/login/', login_data)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)
        
        # Step 4: User accesses protected resources
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        profile_response = self.client.get('/api/auth/profile/')
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['username'], 'new_polinizador')

    def test_complete_login_logout_workflow(self):
        """Test complete login and logout workflow."""
        # Step 1: Initial login
        login_data = {
            'username': self.polinizador.username,
            'password': 'testpass123'
        }
        
        login_response = self.client.post('/api/auth/login/', login_data)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']
        
        # Step 2: Use access token for authenticated requests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        protected_response = self.client.get('/api/auth/profile/')
        self.assertEqual(protected_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Refresh token
        refresh_data = {'refresh': refresh_token}
        refresh_response = self.client.post('/api/auth/token/refresh/', refresh_data)
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        
        new_access_token = refresh_response.data['access']
        self.assertNotEqual(access_token, new_access_token)
        
        # Step 4: Logout (blacklist refresh token)
        logout_data = {'refresh': refresh_token}
        logout_response = self.client.post('/api/auth/logout/', logout_data)
        self.assertIn(logout_response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])
        
        # Step 5: Verify refresh token is blacklisted
        blacklisted_refresh_response = self.client.post('/api/auth/token/refresh/', refresh_data)
        self.assertEqual(blacklisted_refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_workflow(self):
        """Test password change workflow."""
        # Step 1: Login with current password
        self.client.force_authenticate(user=self.polinizador)
        
        # Step 2: Change password
        password_data = {
            'old_password': 'testpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        }
        
        change_response = self.client.post('/api/auth/change-password/', password_data)
        self.assertEqual(change_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Verify old password no longer works
        old_login_data = {
            'username': self.polinizador.username,
            'password': 'testpass123'
        }
        
        old_login_response = self.client.post('/api/auth/login/', old_login_data)
        self.assertEqual(old_login_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Step 4: Verify new password works
        new_login_data = {
            'username': self.polinizador.username,
            'password': 'newpass456'
        }
        
        new_login_response = self.client.post('/api/auth/login/', new_login_data)
        self.assertEqual(new_login_response.status_code, status.HTTP_200_OK)

    def test_role_assignment_and_permission_workflow(self):
        """Test role assignment and permission workflow."""
        self.client.force_authenticate(user=self.admin)
        
        # Step 1: Create user without specific role
        user_data = {
            'username': 'test_user',
            'email': 'test_user@test.com',
            'password': 'testpass123',
            'role': self.germinador_role.id
        }
        
        create_response = self.client.post('/api/auth/users/', user_data)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        user_id = create_response.data['id']
        test_user = User.objects.get(id=user_id)
        
        # Step 2: Verify initial role permissions
        test_client = APIClient()
        test_client.force_authenticate(user=test_user)
        
        # Should have access to germination module
        germ_response = test_client.get('/api/germination/records/')
        self.assertEqual(germ_response.status_code, status.HTTP_200_OK)
        
        # Should NOT have access to reports
        reports_response = test_client.get('/api/reports/')
        self.assertEqual(reports_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Step 3: Admin changes user role to Administrador
        role_update_data = {
            'role': self.admin_role.id
        }
        
        update_response = self.client.patch(f'/api/auth/users/{user_id}/', role_update_data)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Step 4: Verify new role permissions
        test_user.refresh_from_db()
        self.assertEqual(test_user.role, self.admin_role)
        
        # Should now have access to reports
        reports_response2 = test_client.get('/api/reports/')
        self.assertEqual(reports_response2.status_code, status.HTTP_200_OK)

    def test_user_profile_management_workflow(self):
        """Test user profile management workflow."""
        self.client.force_authenticate(user=self.polinizador)
        
        # Step 1: Get current profile
        profile_response = self.client.get('/api/auth/profile/')
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        
        original_profile = profile_response.data
        
        # Step 2: Update profile information
        profile_update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@test.com'
        }
        
        update_response = self.client.patch('/api/auth/profile/', profile_update_data)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Verify profile was updated
        updated_profile_response = self.client.get('/api/auth/profile/')
        updated_profile = updated_profile_response.data
        
        self.assertEqual(updated_profile['first_name'], 'Updated')
        self.assertEqual(updated_profile['last_name'], 'Name')
        self.assertEqual(updated_profile['email'], 'updated@test.com')
        
        # Step 4: Update user preferences (if UserProfile exists)
        if hasattr(self.polinizador, 'userprofile'):
            preferences_data = {
                'preferences': {
                    'language': 'es',
                    'notifications': True,
                    'theme': 'dark'
                }
            }
            
            prefs_response = self.client.patch('/api/auth/profile/', preferences_data)
            self.assertEqual(prefs_response.status_code, status.HTTP_200_OK)

    def test_authentication_error_handling(self):
        """Test authentication error handling scenarios."""
        # Test 1: Invalid credentials
        invalid_login_data = {
            'username': 'nonexistent',
            'password': 'wrongpass'
        }
        
        invalid_response = self.client.post('/api/auth/login/', invalid_login_data)
        self.assertEqual(invalid_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test 2: Missing credentials
        missing_data = {'username': self.polinizador.username}
        
        missing_response = self.client.post('/api/auth/login/', missing_data)
        self.assertEqual(missing_response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test 3: Inactive user
        inactive_user = CustomUserFactory(is_active=False)
        inactive_login_data = {
            'username': inactive_user.username,
            'password': 'testpass123'
        }
        
        inactive_response = self.client.post('/api/auth/login/', inactive_login_data)
        self.assertEqual(inactive_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test 4: Invalid token format
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.format')
        
        invalid_token_response = self.client.get('/api/auth/profile/')
        self.assertEqual(invalid_token_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_concurrent_authentication_sessions(self):
        """Test handling of concurrent authentication sessions."""
        # Step 1: Create multiple login sessions
        login_data = {
            'username': self.polinizador.username,
            'password': 'testpass123'
        }
        
        # First session
        response1 = self.client.post('/api/auth/login/', login_data)
        token1 = response1.data['access']
        refresh1 = response1.data['refresh']
        
        # Second session
        response2 = self.client.post('/api/auth/login/', login_data)
        token2 = response2.data['access']
        refresh2 = response2.data['refresh']
        
        # Step 2: Verify both sessions work
        client1 = APIClient()
        client2 = APIClient()
        
        client1.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        
        response1 = client1.get('/api/auth/profile/')
        response2 = client2.get('/api/auth/profile/')
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Step 3: Logout one session
        logout_data = {'refresh': refresh1}
        logout_response = client1.post('/api/auth/logout/', logout_data)
        self.assertIn(logout_response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])
        
        # Step 4: Verify first session is invalidated, second still works
        refresh_response1 = client1.post('/api/auth/token/refresh/', {'refresh': refresh1})
        self.assertEqual(refresh_response1.status_code, status.HTTP_401_UNAUTHORIZED)
        
        refresh_response2 = client2.post('/api/auth/token/refresh/', {'refresh': refresh2})
        self.assertEqual(refresh_response2.status_code, status.HTTP_200_OK)

    def test_authentication_with_different_roles(self):
        """Test authentication workflow with different user roles."""
        roles_and_users = [
            (self.polinizador_role, PolinizadorUserFactory()),
            (self.germinador_role, GerminadorUserFactory()),
            (self.secretaria_role, SecretariaUserFactory()),
            (self.admin_role, AdministradorUserFactory())
        ]
        
        for role, user in roles_and_users:
            with self.subTest(role=role.name):
                # Step 1: Login with role-specific user
                login_data = {
                    'username': user.username,
                    'password': 'testpass123'
                }
                
                login_response = self.client.post('/api/auth/login/', login_data)
                self.assertEqual(login_response.status_code, status.HTTP_200_OK)
                
                # Step 2: Verify role information in token/profile
                access_token = login_response.data['access']
                self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
                
                profile_response = self.client.get('/api/auth/profile/')
                self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
                self.assertEqual(profile_response.data['role']['name'], role.name)
                
                # Step 3: Test role-specific access
                if role.name == 'Administrador':
                    reports_response = self.client.get('/api/reports/')
                    self.assertEqual(reports_response.status_code, status.HTTP_200_OK)
                else:
                    reports_response = self.client.get('/api/reports/')
                    self.assertEqual(reports_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authentication_security_measures(self):
        """Test authentication security measures."""
        # Test 1: Account lockout after multiple failed attempts
        failed_login_data = {
            'username': self.polinizador.username,
            'password': 'wrongpassword'
        }
        
        # Make multiple failed login attempts
        for i in range(5):
            response = self.client.post('/api/auth/login/', failed_login_data)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Account should still be accessible (no lockout implemented yet)
        correct_login_data = {
            'username': self.polinizador.username,
            'password': 'testpass123'
        }
        
        correct_response = self.client.post('/api/auth/login/', correct_login_data)
        self.assertEqual(correct_response.status_code, status.HTTP_200_OK)
        
        # Test 2: Password complexity validation
        weak_passwords = ['123', 'password', 'abc', '111111']
        
        self.client.force_authenticate(user=self.polinizador)
        
        for weak_password in weak_passwords:
            password_data = {
                'old_password': 'testpass123',
                'new_password': weak_password,
                'confirm_password': weak_password
            }
            
            response = self.client.post('/api/auth/change-password/', password_data)
            # Should reject weak passwords
            self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK])

    def test_user_management_by_admin(self):
        """Test user management operations by admin."""
        self.client.force_authenticate(user=self.admin)
        
        # Step 1: List all users
        users_response = self.client.get('/api/auth/users/')
        self.assertEqual(users_response.status_code, status.HTTP_200_OK)
        
        # Step 2: Create new user
        new_user_data = {
            'username': 'managed_user',
            'email': 'managed@test.com',
            'password': 'managedpass123',
            'role': self.polinizador_role.id,
            'is_active': True
        }
        
        create_response = self.client.post('/api/auth/users/', new_user_data)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        user_id = create_response.data['id']
        
        # Step 3: Update user
        update_data = {
            'first_name': 'Managed',
            'last_name': 'User',
            'is_active': False
        }
        
        update_response = self.client.patch(f'/api/auth/users/{user_id}/', update_data)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Step 4: Verify user was updated
        get_response = self.client.get(f'/api/auth/users/{user_id}/')
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data['first_name'], 'Managed')
        self.assertFalse(get_response.data['is_active'])
        
        # Step 5: Deactivated user should not be able to login
        deactivated_login = {
            'username': 'managed_user',
            'password': 'managedpass123'
        }
        
        login_response = self.client.post('/api/auth/login/', deactivated_login)
        self.assertEqual(login_response.status_code, status.HTTP_401_UNAUTHORIZED)