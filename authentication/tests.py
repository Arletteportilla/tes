from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import Role, UserProfile
import json


User = get_user_model()


class RoleModelTest(TestCase):
    """
    Test cases for Role model.
    """
    
    def setUp(self):
        """Set up test data."""
        self.role_data = {
            'name': 'Polinizador',
            'description': 'Usuario encargado de procesos de polinización'
        }
    
    def test_create_role(self):
        """Test creating a role with valid data."""
        role = Role.objects.create(**self.role_data)
        self.assertEqual(role.name, 'Polinizador')
        self.assertEqual(role.description, 'Usuario encargado de procesos de polinización')
        self.assertTrue(role.is_active)
        self.assertIsNotNone(role.created_at)
        self.assertIsNotNone(role.updated_at)
    
    def test_role_str_representation(self):
        """Test string representation of role."""
        role = Role.objects.create(**self.role_data)
        self.assertEqual(str(role), 'Polinizador')
    
    def test_role_unique_name(self):
        """Test that role names must be unique."""
        Role.objects.create(**self.role_data)
        with self.assertRaises(IntegrityError):
            Role.objects.create(**self.role_data)
    
    def test_role_default_permissions(self):
        """Test that roles get default permissions when created."""
        role = Role.objects.create(**self.role_data)
        expected_permissions = {
            'modules': ['pollination'],
            'can_create': True,
            'can_read': True,
            'can_update': True,
            'can_delete': False,
            'can_generate_reports': False
        }
        self.assertEqual(role.permissions, expected_permissions)
    
    def test_role_custom_permissions(self):
        """Test creating role with custom permissions."""
        custom_permissions = {'modules': ['custom'], 'can_create': False}
        role = Role.objects.create(
            name='Germinador',
            description='Test role',
            permissions=custom_permissions
        )
        self.assertEqual(role.permissions, custom_permissions)
    
    def test_get_default_permissions_for_all_roles(self):
        """Test default permissions for all role types."""
        role_types = ['Polinizador', 'Germinador', 'Secretaria', 'Administrador']
        
        for role_type in role_types:
            role = Role(name=role_type)
            permissions = role.get_default_permissions()
            self.assertIn('modules', permissions)
            self.assertIn('can_create', permissions)
            self.assertIn('can_read', permissions)
            self.assertIn('can_update', permissions)
            self.assertIn('can_delete', permissions)
            self.assertIn('can_generate_reports', permissions)
    
    def test_administrador_permissions(self):
        """Test that Administrador role has full permissions."""
        role = Role.objects.create(name='Administrador')
        self.assertTrue(role.permissions['can_delete'])
        self.assertTrue(role.permissions['can_generate_reports'])
        self.assertIn('reports', role.permissions['modules'])
    
    def test_polinizador_permissions(self):
        """Test that Polinizador role has limited permissions."""
        role = Role.objects.create(name='Polinizador')
        self.assertFalse(role.permissions['can_delete'])
        self.assertFalse(role.permissions['can_generate_reports'])
        self.assertEqual(role.permissions['modules'], ['pollination'])


class CustomUserModelTest(TestCase):
    """
    Test cases for CustomUser model.
    """
    
    def setUp(self):
        """Set up test data."""
        self.role = Role.objects.create(name='Polinizador')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'employee_id': 'EMP001',
            'phone_number': '+1234567890'
        }
    
    def test_create_user(self):
        """Test creating a user with valid data."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.employee_id, 'EMP001')
        self.assertEqual(user.phone_number, '+1234567890')
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
    
    def test_user_str_representation(self):
        """Test string representation of user."""
        user = User.objects.create_user(**self.user_data)
        expected_str = f"{user.username} - {user.get_full_name()}"
        self.assertEqual(str(user), expected_str)
    
    def test_user_with_role(self):
        """Test creating user with role."""
        user = User.objects.create_user(role=self.role, **self.user_data)
        self.assertEqual(user.role, self.role)
        self.assertEqual(user.get_role_name(), 'Polinizador')
    
    def test_user_unique_employee_id(self):
        """Test that employee IDs must be unique."""
        User.objects.create_user(**self.user_data)
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='testuser2',
                email='test2@example.com',
                employee_id='EMP001'
            )
    
    def test_user_has_role_method(self):
        """Test has_role method."""
        user = User.objects.create_user(role=self.role, **self.user_data)
        self.assertTrue(user.has_role('Polinizador'))
        self.assertFalse(user.has_role('Administrador'))
    
    def test_user_has_module_permission(self):
        """Test has_module_permission method."""
        user = User.objects.create_user(role=self.role, **self.user_data)
        self.assertTrue(user.has_module_permission('pollination'))
        self.assertFalse(user.has_module_permission('reports'))
    
    def test_superuser_permissions(self):
        """Test that superuser has all permissions."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        self.assertTrue(user.has_module_permission('any_module'))
        self.assertTrue(user.can_delete_records())
        self.assertTrue(user.can_generate_reports())
    
    def test_user_can_delete_records(self):
        """Test can_delete_records method."""
        # Regular user cannot delete
        user = User.objects.create_user(role=self.role, **self.user_data)
        self.assertFalse(user.can_delete_records())
        
        # Admin can delete
        admin_role = Role.objects.create(name='Administrador')
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            role=admin_role
        )
        self.assertTrue(admin_user.can_delete_records())
    
    def test_user_can_generate_reports(self):
        """Test can_generate_reports method."""
        # Regular user cannot generate reports
        user = User.objects.create_user(role=self.role, **self.user_data)
        self.assertFalse(user.can_generate_reports())
        
        # Admin can generate reports
        admin_role = Role.objects.create(name='Administrador')
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            role=admin_role
        )
        self.assertTrue(admin_user.can_generate_reports())
    
    def test_phone_number_validation(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_phones = ['+1234567890', '1234567890', '+123456789012345']
        for i, phone in enumerate(valid_phones):
            user_data = self.user_data.copy()
            user_data['phone_number'] = phone
            user_data['username'] = f'user_phone_{i}'
            user_data['email'] = f'user_phone_{i}@example.com'
            user_data['employee_id'] = f'EMP_PHONE_{i}'
            user = User.objects.create_user(**user_data)
            self.assertEqual(user.phone_number, phone)
    
    def test_user_without_role(self):
        """Test user behavior without assigned role."""
        user = User.objects.create_user(**self.user_data)
        self.assertIsNone(user.get_role_name())
        self.assertFalse(user.has_role('any_role'))
        self.assertFalse(user.has_module_permission('any_module'))
        self.assertFalse(user.can_delete_records())
        self.assertFalse(user.can_generate_reports())


class UserProfileModelTest(TestCase):
    """
    Test cases for UserProfile model.
    """
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.profile_data = {
            'user': self.user,
            'department': 'Investigación',
            'position': 'Técnico en Polinización',
            'bio': 'Especialista en procesos de polinización',
            'address': 'Calle 123 #45-67',
            'emergency_contact_name': 'Jane Doe',
            'emergency_contact_phone': '+0987654321'
        }
    
    def test_create_user_profile(self):
        """Test creating a user profile."""
        profile = UserProfile.objects.create(**self.profile_data)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.department, 'Investigación')
        self.assertEqual(profile.position, 'Técnico en Polinización')
        self.assertEqual(profile.bio, 'Especialista en procesos de polinización')
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
    
    def test_profile_str_representation(self):
        """Test string representation of profile."""
        profile = UserProfile.objects.create(**self.profile_data)
        expected_str = f"Perfil de {self.user.username}"
        self.assertEqual(str(profile), expected_str)
    
    def test_get_full_profile_name(self):
        """Test get_full_profile_name method."""
        profile = UserProfile.objects.create(**self.profile_data)
        expected_name = f"{self.user.get_full_name()} - {profile.position}"
        self.assertEqual(profile.get_full_profile_name(), expected_name)
    
    def test_get_full_profile_name_without_position(self):
        """Test get_full_profile_name method without position."""
        profile_data = self.profile_data.copy()
        profile_data['position'] = ''
        profile = UserProfile.objects.create(**profile_data)
        expected_name = self.user.get_full_name()
        self.assertEqual(profile.get_full_profile_name(), expected_name)
    
    def test_profile_one_to_one_relationship(self):
        """Test one-to-one relationship with user."""
        profile = UserProfile.objects.create(**self.profile_data)
        self.assertEqual(self.user.profile, profile)
        
        # Test that creating another profile for the same user raises error
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(**self.profile_data)
    
    def test_profile_preferences_json_field(self):
        """Test preferences JSON field."""
        preferences = {
            'theme': 'dark',
            'language': 'es',
            'notifications': True,
            'email_alerts': False
        }
        profile_data = self.profile_data.copy()
        profile_data['preferences'] = preferences
        profile = UserProfile.objects.create(**profile_data)
        self.assertEqual(profile.preferences, preferences)
    
    def test_emergency_contact_phone_validation(self):
        """Test emergency contact phone validation."""
        valid_phones = ['+1234567890', '1234567890']
        for i, phone in enumerate(valid_phones):
            profile_data = self.profile_data.copy()
            profile_data['emergency_contact_phone'] = phone
            # Create new user for each test to avoid unique constraint issues
            user = User.objects.create_user(
                username=f'user_emergency_{i}',
                email=f'user_emergency_{i}@example.com'
            )
            profile_data['user'] = user
            profile = UserProfile.objects.create(**profile_data)
            self.assertEqual(profile.emergency_contact_phone, phone)
    
    def test_profile_cascade_delete(self):
        """Test that profile is deleted when user is deleted."""
        profile = UserProfile.objects.create(**self.profile_data)
        profile_id = profile.id
        
        # Delete user
        self.user.delete()
        
        # Profile should be deleted too
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)


class ModelIntegrationTest(TestCase):
    """
    Integration tests for authentication models.
    """
    
    def test_complete_user_setup(self):
        """Test creating a complete user with role and profile."""
        # Create role
        role = Role.objects.create(
            name='Secretaria',
            description='Personal administrativo'
        )
        
        # Create user
        user = User.objects.create_user(
            username='secretary',
            email='secretary@example.com',
            first_name='Maria',
            last_name='Garcia',
            role=role,
            employee_id='SEC001',
            phone_number='+1234567890'
        )
        
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            department='Administración',
            position='Secretaria Ejecutiva',
            bio='Encargada de soporte administrativo',
            preferences={'theme': 'light', 'language': 'es'}
        )
        
        # Test relationships and methods
        self.assertEqual(user.role.name, 'Secretaria')
        self.assertTrue(user.has_role('Secretaria'))
        self.assertTrue(user.has_module_permission('pollination'))
        self.assertTrue(user.has_module_permission('germination'))
        self.assertFalse(user.can_generate_reports())
        
        self.assertEqual(user.profile, profile)
        self.assertIn('Secretaria Ejecutiva', profile.get_full_profile_name())
    
    def test_role_permissions_inheritance(self):
        """Test that users inherit permissions from their roles."""
        roles_and_modules = [
            ('Polinizador', ['pollination']),
            ('Germinador', ['germination']),
            ('Secretaria', ['pollination', 'germination', 'alerts']),
            ('Administrador', ['pollination', 'germination', 'alerts', 'reports', 'authentication'])
        ]
        
        for role_name, expected_modules in roles_and_modules:
            role = Role.objects.create(name=role_name)
            user = User.objects.create_user(
                username=f'user_{role_name.lower()}',
                email=f'{role_name.lower()}@example.com',
                role=role
            )
            
            for module in expected_modules:
                self.assertTrue(
                    user.has_module_permission(module),
                    f"User with role {role_name} should have access to {module}"
                )
            
            # Test admin-specific permissions
            if role_name == 'Administrador':
                self.assertTrue(user.can_delete_records())
                self.assertTrue(user.can_generate_reports())
            else:
                self.assertFalse(user.can_delete_records())
                self.assertFalse(user.can_generate_reports())
