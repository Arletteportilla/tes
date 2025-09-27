from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Role, UserProfile
import json

User = get_user_model()


class AuthenticationViewsTest(APITestCase):
    """
    Test cases for authentication views.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create roles
        self.polinizador_role = Role.objects.create(name='Polinizador')
        self.admin_role = Role.objects.create(name='Administrador')
        
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=self.polinizador_role,
            employee_id='EMP001'
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role=self.admin_role,
            employee_id='ADM001'
        )
        
        # URLs
        self.login_url = reverse('authentication:login')
        self.token_url = reverse('authentication:token_obtain_pair')
        self.refresh_url = reverse('authentication:token_refresh')
        self.logout_url = reverse('authentication:logout')
        self.profile_url = reverse('authentication:user_profile')
        self.password_change_url = reverse('authentication:password_change')
        self.register_url = reverse('authentication:user_registration')
        self.roles_url = reverse('authentication:role_list')
        self.status_url = reverse('authentication:auth_status')
        self.permissions_url = reverse('authentication:user_permissions')
    
    def test_login_view_success(self):
        """Test successful login."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_login_view_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
    
    def test_login_view_inactive_user(self):
        """Test login with inactive user."""
        self.user.is_active = False
        self.user.save()
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_token_obtain_pair_view(self):
        """Test JWT token obtain pair view."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_token_refresh_view(self):
        """Test JWT token refresh view."""
        # First get tokens
        refresh = RefreshToken.for_user(self.user)
        
        data = {'refresh': str(refresh)}
        response = self.client.post(self.refresh_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('user', response.data)
    
    def test_logout_view_success(self):
        """Test successful logout."""
        refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(user=self.user)
        
        data = {'refresh': str(refresh)}
        response = self.client.post(self.logout_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_logout_view_without_token(self):
        """Test logout without refresh token."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.logout_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_profile_view_get(self):
        """Test getting user profile."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['role']['name'], 'Polinizador')
    
    def test_user_profile_view_update(self):
        """Test updating user profile."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+1234567890'
        }
        response = self.client.patch(self.profile_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'Name')
        self.assertEqual(response.data['phone_number'], '+1234567890')
    
    def test_password_change_view_success(self):
        """Test successful password change."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        response = self.client.post(self.password_change_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))
    
    def test_password_change_view_wrong_old_password(self):
        """Test password change with wrong old password."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        response = self.client.post(self.password_change_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)
    
    def test_password_change_view_mismatched_passwords(self):
        """Test password change with mismatched new passwords."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass123'
        }
        response = self.client.post(self.password_change_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
    
    def test_user_registration_view_admin_success(self):
        """Test user registration by admin."""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'employee_id': 'EMP002'
        }
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'newuser')
        
        # Verify user was created
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.email, 'newuser@example.com')
    
    def test_user_registration_view_non_admin_forbidden(self):
        """Test user registration by non-admin user."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_role_list_view(self):
        """Test role list view."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.roles_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response has results (paginated) or is a direct list
        if 'results' in response.data:
            roles_data = response.data['results']
        else:
            roles_data = response.data
        
        self.assertGreaterEqual(len(roles_data), 2)
        role_names = [role['name'] for role in roles_data]
        self.assertIn('Polinizador', role_names)
        self.assertIn('Administrador', role_names)
    
    def test_auth_status_view(self):
        """Test authentication status view."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_auth_status_view_unauthenticated(self):
        """Test authentication status view without authentication."""
        response = self.client.get(self.status_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_permissions_view(self):
        """Test user permissions view."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.permissions_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'Polinizador')
        self.assertTrue(response.data['modules']['pollination'])
        self.assertFalse(response.data['modules']['reports'])
        self.assertFalse(response.data['can_delete_records'])
        self.assertFalse(response.data['can_generate_reports'])
    
    def test_user_permissions_view_admin(self):
        """Test user permissions view for admin."""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.permissions_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'Administrador')
        self.assertTrue(response.data['modules']['pollination'])
        self.assertTrue(response.data['modules']['reports'])
        self.assertTrue(response.data['can_delete_records'])
        self.assertTrue(response.data['can_generate_reports'])
    
    def test_unauthenticated_access_to_protected_views(self):
        """Test that protected views require authentication."""
        protected_urls = [
            self.profile_url,
            self.password_change_url,
            self.register_url,
            self.roles_url,
            self.status_url,
            self.permissions_url,
            self.logout_url
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 
                status.HTTP_401_UNAUTHORIZED,
                f"URL {url} should require authentication"
            )


class JWTTokenTest(APITestCase):
    """
    Test JWT token functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        self.role = Role.objects.create(name='Polinizador')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role,
            employee_id='EMP001'
        )
    
    def test_jwt_token_contains_custom_claims(self):
        """Test that JWT tokens contain custom claims."""
        from authentication.serializers import CustomTokenObtainPairSerializer
        
        # Use the custom serializer to generate token with custom claims
        refresh = CustomTokenObtainPairSerializer.get_token(self.user)
        access = refresh.access_token
        
        # Check custom claims
        self.assertEqual(access['username'], 'testuser')
        self.assertEqual(access['email'], 'test@example.com')
        self.assertEqual(access['role'], 'Polinizador')
        self.assertEqual(access['employee_id'], 'EMP001')
    
    def test_jwt_token_authentication(self):
        """Test JWT token authentication."""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        # Use token to authenticate
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = self.client.get(reverse('authentication:auth_status'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_invalid_jwt_token(self):
        """Test authentication with invalid JWT token."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        response = self.client.get(reverse('authentication:auth_status'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileIntegrationTest(APITestCase):
    """
    Integration tests for user profile functionality.
    """
    
    def setUp(self):
        """Set up test data."""
        self.role = Role.objects.create(name='Secretaria')
        self.user = User.objects.create_user(
            username='secretary',
            email='secretary@example.com',
            password='secretpass123',
            first_name='Maria',
            last_name='Garcia',
            role=self.role,
            employee_id='SEC001'
        )
        
        # Create user profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            department='Administración',
            position='Secretaria Ejecutiva',
            bio='Encargada de soporte administrativo'
        )
    
    def test_user_profile_in_user_data(self):
        """Test that user profile is included in user data."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(reverse('authentication:user_profile'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile', response.data)
        self.assertEqual(response.data['profile']['department'], 'Administración')
        self.assertEqual(response.data['profile']['position'], 'Secretaria Ejecutiva')
    
    def test_complete_authentication_flow(self):
        """Test complete authentication flow with profile."""
        # Login
        login_data = {
            'username': 'secretary',
            'password': 'secretpass123'
        }
        login_response = self.client.post(
            reverse('authentication:login'), 
            login_data
        )
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Use access token
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Check permissions
        permissions_response = self.client.get(
            reverse('authentication:user_permissions')
        )
        
        self.assertEqual(permissions_response.status_code, status.HTTP_200_OK)
        self.assertEqual(permissions_response.data['role'], 'Secretaria')
        self.assertTrue(permissions_response.data['modules']['pollination'])
        self.assertTrue(permissions_response.data['modules']['germination'])
        self.assertTrue(permissions_response.data['modules']['alerts'])
        self.assertFalse(permissions_response.data['modules']['reports'])
        
        # Logout
        refresh_token = login_response.data['refresh']
        logout_response = self.client.post(
            reverse('authentication:logout'),
            {'refresh': refresh_token}
        )
        
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)