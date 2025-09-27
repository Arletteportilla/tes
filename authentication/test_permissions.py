from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import Mock, patch
from .models import Role
from .permissions import (
    RoleBasedPermission,
    ModulePermission,
    PollinationModulePermission,
    GerminationModulePermission,
    AlertsModulePermission,
    ReportsModulePermission,
    AuthenticationModulePermission,
    CanDeleteRecordsPermission,
    CanGenerateReportsPermission,
    IsOwnerOrAdminPermission,
    require_role,
    require_module_permission,
    require_admin_permission,
    require_delete_permission,
    require_reports_permission,
    RoleRequiredMixin,
    ModulePermissionMixin,
    AdminRequiredMixin,
    DeletePermissionMixin,
    ReportsPermissionMixin
)
from .middleware import (
    RoleBasedPermissionMiddleware,
    UserActivityMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware
)

User = get_user_model()


class PermissionClassesTest(TestCase):
    """
    Test cases for permission classes.
    """
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create roles
        self.polinizador_role = Role.objects.create(name='Polinizador')
        self.germinador_role = Role.objects.create(name='Germinador')
        self.secretaria_role = Role.objects.create(name='Secretaria')
        self.admin_role = Role.objects.create(name='Administrador')
        
        # Create users
        self.polinizador = User.objects.create_user(
            username='polinizador',
            password='pass123',
            role=self.polinizador_role
        )
        
        self.germinador = User.objects.create_user(
            username='germinador',
            password='pass123',
            role=self.germinador_role
        )
        
        self.secretaria = User.objects.create_user(
            username='secretaria',
            password='pass123',
            role=self.secretaria_role
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            password='pass123',
            role=self.admin_role
        )
        
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='pass123',
            email='super@example.com'
        )
        
        self.anonymous_user = None
    
    def test_role_based_permission(self):
        """Test RoleBasedPermission class."""
        permission = RoleBasedPermission()
        view = Mock()
        
        # Test with authenticated user
        request = self.factory.get('/')
        request.user = self.polinizador
        self.assertTrue(permission.has_permission(request, view))
        
        # Test with superuser
        request.user = self.superuser
        self.assertTrue(permission.has_permission(request, view))
        
        # Test with unauthenticated user
        request.user = self.anonymous_user
        self.assertFalse(permission.has_permission(request, view))
        
        # Test with user without role
        user_no_role = User.objects.create_user(username='norole', password='pass123')
        request.user = user_no_role
        self.assertFalse(permission.has_permission(request, view))
    
    def test_module_permissions(self):
        """Test module-specific permission classes."""
        # Create a simple view object without required_module attribute
        class SimpleView:
            pass
        
        view = SimpleView()
        request = self.factory.get('/')
        
        # Test PollinationModulePermission
        permission = PollinationModulePermission()
        
        request.user = self.polinizador
        self.assertTrue(permission.has_permission(request, view))
        
        request.user = self.germinador
        self.assertFalse(permission.has_permission(request, view))
        
        request.user = self.secretaria
        self.assertTrue(permission.has_permission(request, view))
        
        request.user = self.admin
        self.assertTrue(permission.has_permission(request, view))
        
        # Test GerminationModulePermission
        permission = GerminationModulePermission()
        
        request.user = self.polinizador
        self.assertFalse(permission.has_permission(request, view))
        
        request.user = self.germinador
        self.assertTrue(permission.has_permission(request, view))
        
        request.user = self.secretaria
        self.assertTrue(permission.has_permission(request, view))
        
        # Test ReportsModulePermission
        permission = ReportsModulePermission()
        
        request.user = self.polinizador
        self.assertFalse(permission.has_permission(request, view))
        
        request.user = self.admin
        self.assertTrue(permission.has_permission(request, view))
    
    def test_can_delete_records_permission(self):
        """Test CanDeleteRecordsPermission class."""
        permission = CanDeleteRecordsPermission()
        view = Mock()
        request = self.factory.delete('/')
        
        # Only admin can delete
        request.user = self.polinizador
        self.assertFalse(permission.has_permission(request, view))
        
        request.user = self.admin
        self.assertTrue(permission.has_permission(request, view))
        
        request.user = self.superuser
        self.assertTrue(permission.has_permission(request, view))
    
    def test_can_generate_reports_permission(self):
        """Test CanGenerateReportsPermission class."""
        permission = CanGenerateReportsPermission()
        view = Mock()
        request = self.factory.get('/')
        
        # Only admin can generate reports
        request.user = self.secretaria
        self.assertFalse(permission.has_permission(request, view))
        
        request.user = self.admin
        self.assertTrue(permission.has_permission(request, view))
    
    def test_is_owner_or_admin_permission(self):
        """Test IsOwnerOrAdminPermission class."""
        permission = IsOwnerOrAdminPermission()
        view = Mock()
        request = self.factory.get('/')
        
        # Create mock object with created_by field
        obj = Mock()
        obj.created_by = self.polinizador
        
        # Owner can access
        request.user = self.polinizador
        self.assertTrue(permission.has_object_permission(request, view, obj))
        
        # Non-owner cannot access
        request.user = self.germinador
        self.assertFalse(permission.has_object_permission(request, view, obj))
        
        # Admin can access
        request.user = self.admin
        self.assertTrue(permission.has_object_permission(request, view, obj))


class PermissionDecoratorsTest(TestCase):
    """
    Test cases for permission decorators.
    """
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create roles and users
        self.admin_role = Role.objects.create(name='Administrador')
        self.polinizador_role = Role.objects.create(name='Polinizador')
        
        self.admin = User.objects.create_user(
            username='admin',
            password='pass123',
            role=self.admin_role
        )
        
        self.polinizador = User.objects.create_user(
            username='polinizador',
            password='pass123',
            role=self.polinizador_role
        )
    
    def test_require_role_decorator(self):
        """Test require_role decorator."""
        @require_role('Administrador')
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Test with admin user
        request = self.factory.get('/')
        request.user = self.admin
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        
        # Test with non-admin user
        request.user = self.polinizador
        with self.assertRaises(Exception):  # PermissionDenied or similar
            test_view(request)
    
    def test_require_module_permission_decorator(self):
        """Test require_module_permission decorator."""
        @require_module_permission('pollination')
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Test with user who has pollination permission
        request = self.factory.get('/')
        request.user = self.polinizador
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_require_admin_permission_decorator(self):
        """Test require_admin_permission decorator."""
        @require_admin_permission
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Test with admin user
        request = self.factory.get('/')
        request.user = self.admin
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        
        # Test with non-admin user
        request.user = self.polinizador
        with self.assertRaises(Exception):
            test_view(request)


class PermissionMixinsTest(TestCase):
    """
    Test cases for permission mixins.
    """
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create roles and users
        self.admin_role = Role.objects.create(name='Administrador')
        self.polinizador_role = Role.objects.create(name='Polinizador')
        
        self.admin = User.objects.create_user(
            username='admin',
            password='pass123',
            role=self.admin_role
        )
        
        self.polinizador = User.objects.create_user(
            username='polinizador',
            password='pass123',
            role=self.polinizador_role
        )
    
    def test_role_required_mixin(self):
        """Test RoleRequiredMixin."""
        class TestView(RoleRequiredMixin, APIView):
            required_role = 'Administrador'
            
            def get(self, request):
                return Response({'success': True})
        
        view = TestView.as_view()
        
        # Test with admin user
        request = self.factory.get('/')
        request.user = self.admin
        response = view(request)
        self.assertEqual(response.status_code, 200)
        
        # Test with non-admin user
        request.user = self.polinizador
        with self.assertRaises(Exception):
            view(request)
    
    def test_module_permission_mixin(self):
        """Test ModulePermissionMixin."""
        class TestView(ModulePermissionMixin, APIView):
            required_module = 'pollination'
            
            def get(self, request):
                return Response({'success': True})
        
        view = TestView.as_view()
        
        # Test with user who has pollination permission
        request = self.factory.get('/')
        request.user = self.polinizador
        response = view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_admin_required_mixin(self):
        """Test AdminRequiredMixin."""
        class TestView(AdminRequiredMixin, APIView):
            def get(self, request):
                return Response({'success': True})
        
        view = TestView.as_view()
        
        # Test with admin user
        request = self.factory.get('/')
        request.user = self.admin
        response = view(request)
        self.assertEqual(response.status_code, 200)
        
        # Test with non-admin user
        request.user = self.polinizador
        with self.assertRaises(Exception):
            view(request)
    
    def test_delete_permission_mixin(self):
        """Test DeletePermissionMixin."""
        from django.views import View
        from django.http import JsonResponse
        
        class TestView(DeletePermissionMixin, View):
            def delete(self, request):
                return JsonResponse({'success': True})
        
        view = TestView.as_view()
        
        # Verify admin can delete records
        self.assertTrue(self.admin.can_delete_records(), "Admin should be able to delete records")
        
        # Test with admin user (can delete)
        request = self.factory.delete('/')
        request.user = self.admin
        response = view(request)
        self.assertEqual(response.status_code, 200)
        
        # Test with non-admin user (cannot delete)
        request = self.factory.delete('/')
        request.user = self.polinizador
        with self.assertRaises(Exception):
            view(request)


class MiddlewareTest(TestCase):
    """
    Test cases for middleware classes.
    """
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create roles and users
        self.admin_role = Role.objects.create(name='Administrador')
        self.admin = User.objects.create_user(
            username='admin',
            password='pass123',
            role=self.admin_role
        )
    
    def test_security_headers_middleware(self):
        """Test SecurityHeadersMiddleware."""
        middleware = SecurityHeadersMiddleware(lambda request: JsonResponse({}))
        
        request = self.factory.get('/api/test/')
        response = middleware(request)
        
        # Check security headers
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-XSS-Protection'], '1; mode=block')
        self.assertEqual(response['Referrer-Policy'], 'strict-origin-when-cross-origin')
    
    def test_user_activity_middleware(self):
        """Test UserActivityMiddleware."""
        middleware = UserActivityMiddleware(lambda request: JsonResponse({}))
        
        request = self.factory.get('/')
        request.user = self.admin
        
        # Store original last_login
        original_last_login = self.admin.last_login
        
        # Process request
        middleware(request)
        
        # Check that last_login was updated
        self.admin.refresh_from_db()
        self.assertNotEqual(self.admin.last_login, original_last_login)
    
    @patch('authentication.middleware.resolve')
    def test_role_based_permission_middleware_public_url(self, mock_resolve):
        """Test RoleBasedPermissionMiddleware with public URL."""
        middleware = RoleBasedPermissionMiddleware(lambda request: JsonResponse({}))
        
        # Mock resolve to return login URL
        mock_resolved = Mock()
        mock_resolved.namespace = 'authentication'
        mock_resolved.url_name = 'login'
        mock_resolve.return_value = mock_resolved
        
        request = self.factory.post('/api/auth/login/')
        response = middleware(request)
        
        # Should allow access to public URL (middleware returns None for allowed requests)
        # The response we get is from the lambda function, not the middleware
        self.assertEqual(response.status_code, 200)
    
    def test_error_handling_middleware(self):
        """Test ErrorHandlingMiddleware."""
        middleware = ErrorHandlingMiddleware(lambda request: JsonResponse({}))
        
        request = self.factory.get('/api/test/')
        
        # Test with PermissionDenied exception
        from rest_framework.exceptions import PermissionDenied
        exception = PermissionDenied("Test permission denied")
        
        response = middleware.process_exception(request, exception)
        
        self.assertEqual(response.status_code, 403)
        import json
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'PERMISSION_DENIED')


class IntegrationTest(APITestCase):
    """
    Integration tests for the complete permissions system.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create roles
        self.polinizador_role = Role.objects.create(name='Polinizador')
        self.admin_role = Role.objects.create(name='Administrador')
        
        # Create users
        self.polinizador = User.objects.create_user(
            username='polinizador',
            password='pass123',
            role=self.polinizador_role,
            email='pol@example.com'
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            password='pass123',
            role=self.admin_role,
            email='admin@example.com'
        )
    
    def test_complete_permission_flow(self):
        """Test complete permission flow from login to resource access."""
        # Login as polinizador
        login_data = {
            'username': 'polinizador',
            'password': 'pass123'
        }
        login_response = self.client.post('/api/auth/login/', login_data)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Use access token
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Check permissions
        permissions_response = self.client.get('/api/auth/permissions/')
        self.assertEqual(permissions_response.status_code, status.HTTP_200_OK)
        
        permissions_data = permissions_response.data
        self.assertEqual(permissions_data['role'], 'Polinizador')
        self.assertTrue(permissions_data['modules']['pollination'])
        self.assertFalse(permissions_data['modules']['reports'])
        self.assertFalse(permissions_data['can_delete_records'])
        self.assertFalse(permissions_data['can_generate_reports'])
    
    def test_admin_permissions_flow(self):
        """Test admin permissions flow."""
        # Login as admin
        login_data = {
            'username': 'admin',
            'password': 'pass123'
        }
        login_response = self.client.post('/api/auth/login/', login_data)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Use access token
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Check permissions
        permissions_response = self.client.get('/api/auth/permissions/')
        self.assertEqual(permissions_response.status_code, status.HTTP_200_OK)
        
        permissions_data = permissions_response.data
        self.assertEqual(permissions_data['role'], 'Administrador')
        self.assertTrue(permissions_data['modules']['pollination'])
        self.assertTrue(permissions_data['modules']['germination'])
        self.assertTrue(permissions_data['modules']['alerts'])
        self.assertTrue(permissions_data['modules']['reports'])
        self.assertTrue(permissions_data['modules']['authentication'])
        self.assertTrue(permissions_data['can_delete_records'])
        self.assertTrue(permissions_data['can_generate_reports'])
        
        # Test user registration (admin only)
        registration_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        registration_response = self.client.post('/api/auth/register/', registration_data)
        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to protected resources."""
        # Try to access protected resource without authentication
        response = self.client.get('/api/auth/permissions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to register user as non-admin
        self.client.force_authenticate(user=self.polinizador)
        registration_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        registration_response = self.client.post('/api/auth/register/', registration_data)
        self.assertEqual(registration_response.status_code, status.HTTP_403_FORBIDDEN)