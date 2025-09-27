from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from alerts.models import AlertType, Alert, UserAlert
from authentication.models import Role
from pollination.models import PollinationRecord, Plant, PollinationType, ClimateCondition
from germination.models import GerminationRecord, SeedSource, GerminationCondition

User = get_user_model()


class AlertTypeModelTest(TestCase):
    """Test cases for AlertType model"""
    
    def setUp(self):
        self.alert_type_data = {
            'name': 'semanal',
            'description': 'Alerta semanal para seguimiento de registros'
        }
    
    def test_create_alert_type(self):
        """Test creating an AlertType instance"""
        alert_type = AlertType.objects.create(**self.alert_type_data)
        
        self.assertEqual(alert_type.name, 'semanal')
        self.assertEqual(alert_type.description, 'Alerta semanal para seguimiento de registros')
        self.assertTrue(alert_type.is_active)
        self.assertIsNotNone(alert_type.created_at)
        self.assertIsNotNone(alert_type.updated_at)
    
    def test_alert_type_str_representation(self):
        """Test string representation of AlertType"""
        alert_type = AlertType.objects.create(**self.alert_type_data)
        self.assertEqual(str(alert_type), 'Semanal')
    
    def test_alert_type_unique_name(self):
        """Test that alert type names are unique"""
        AlertType.objects.create(**self.alert_type_data)
        
        with self.assertRaises(Exception):
            AlertType.objects.create(**self.alert_type_data)
    
    def test_alert_type_choices(self):
        """Test that only valid choices are accepted"""
        valid_types = ['semanal', 'preventiva', 'frecuente']
        
        for alert_type in valid_types:
            instance = AlertType.objects.create(
                name=alert_type,
                description=f'Test {alert_type} alert'
            )
            self.assertEqual(instance.name, alert_type)


class AlertModelTest(TestCase):
    """Test cases for Alert model"""
    
    def setUp(self):
        # Create test user and role
        self.role = Role.objects.create(
            name='Polinizador',
            description='Test role'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create alert type
        self.alert_type = AlertType.objects.create(
            name='semanal',
            description='Weekly alert'
        )
        
        # Create test data for related models
        self.plant = Plant.objects.create(
            genus='Test Genus',
            species='test species',
            vivero='Test Vivero',
            mesa='Test Mesa',
            pared='Test Pared'
        )
        
        self.pollination_type = PollinationType.objects.create(
            name='Self',
            description='Self pollination'
        )
        
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=60
        )
        
        self.pollination_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=timezone.now().date(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
    
    def test_create_alert(self):
        """Test creating an Alert instance"""
        scheduled_date = timezone.now() + timedelta(days=7)
        
        alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Test Alert',
            message='This is a test alert message',
            scheduled_date=scheduled_date,
            pollination_record=self.pollination_record
        )
        
        self.assertEqual(alert.title, 'Test Alert')
        self.assertEqual(alert.message, 'This is a test alert message')
        self.assertEqual(alert.status, 'pending')
        self.assertEqual(alert.priority, 'medium')
        self.assertEqual(alert.alert_type, self.alert_type)
        self.assertEqual(alert.pollination_record, self.pollination_record)
    
    def test_alert_str_representation(self):
        """Test string representation of Alert"""
        alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Test Alert',
            message='Test message',
            scheduled_date=timezone.now()
        )
        
        self.assertEqual(str(alert), 'Test Alert - Pendiente')
    
    def test_alert_is_expired(self):
        """Test alert expiration check"""
        # Create expired alert
        expired_alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Expired Alert',
            message='This alert has expired',
            scheduled_date=timezone.now(),
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # Create non-expired alert
        active_alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Active Alert',
            message='This alert is still active',
            scheduled_date=timezone.now(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Create alert without expiration
        no_expiry_alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='No Expiry Alert',
            message='This alert never expires',
            scheduled_date=timezone.now()
        )
        
        self.assertTrue(expired_alert.is_expired())
        self.assertFalse(active_alert.is_expired())
        self.assertFalse(no_expiry_alert.is_expired())
    
    def test_mark_as_read(self):
        """Test marking alert as read"""
        alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Test Alert',
            message='Test message',
            scheduled_date=timezone.now()
        )
        
        self.assertEqual(alert.status, 'pending')
        
        alert.mark_as_read()
        alert.refresh_from_db()
        
        self.assertEqual(alert.status, 'read')
    
    def test_mark_as_dismissed(self):
        """Test marking alert as dismissed"""
        alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Test Alert',
            message='Test message',
            scheduled_date=timezone.now()
        )
        
        self.assertEqual(alert.status, 'pending')
        
        alert.mark_as_dismissed()
        alert.refresh_from_db()
        
        self.assertEqual(alert.status, 'dismissed')


class UserAlertModelTest(TestCase):
    """Test cases for UserAlert model"""
    
    def setUp(self):
        # Create test user and role
        self.role = Role.objects.create(
            name='Polinizador',
            description='Test role'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create alert type and alert
        self.alert_type = AlertType.objects.create(
            name='semanal',
            description='Weekly alert'
        )
        
        self.alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Test Alert',
            message='Test message',
            scheduled_date=timezone.now()
        )
    
    def test_create_user_alert(self):
        """Test creating a UserAlert instance"""
        user_alert = UserAlert.objects.create(
            user=self.user,
            alert=self.alert
        )
        
        self.assertEqual(user_alert.user, self.user)
        self.assertEqual(user_alert.alert, self.alert)
        self.assertFalse(user_alert.is_read)
        self.assertFalse(user_alert.is_dismissed)
        self.assertIsNone(user_alert.read_at)
        self.assertIsNone(user_alert.dismissed_at)
    
    def test_user_alert_str_representation(self):
        """Test string representation of UserAlert"""
        user_alert = UserAlert.objects.create(
            user=self.user,
            alert=self.alert
        )
        
        expected_str = f"{self.user.username} - {self.alert.title}"
        self.assertEqual(str(user_alert), expected_str)
    
    def test_user_alert_unique_together(self):
        """Test that user-alert combination is unique"""
        UserAlert.objects.create(user=self.user, alert=self.alert)
        
        with self.assertRaises(Exception):
            UserAlert.objects.create(user=self.user, alert=self.alert)
    
    def test_mark_as_read(self):
        """Test marking user alert as read"""
        user_alert = UserAlert.objects.create(
            user=self.user,
            alert=self.alert
        )
        
        self.assertFalse(user_alert.is_read)
        self.assertIsNone(user_alert.read_at)
        
        user_alert.mark_as_read()
        user_alert.refresh_from_db()
        
        self.assertTrue(user_alert.is_read)
        self.assertIsNotNone(user_alert.read_at)
        
        # Check that main alert is also marked as read
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'read')
    
    def test_mark_as_dismissed(self):
        """Test marking user alert as dismissed"""
        user_alert = UserAlert.objects.create(
            user=self.user,
            alert=self.alert
        )
        
        self.assertFalse(user_alert.is_dismissed)
        self.assertIsNone(user_alert.dismissed_at)
        
        user_alert.mark_as_dismissed()
        user_alert.refresh_from_db()
        
        self.assertTrue(user_alert.is_dismissed)
        self.assertIsNotNone(user_alert.dismissed_at)
        
        # Check that main alert is also marked as dismissed
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'dismissed')
    
    def test_mark_as_read_idempotent(self):
        """Test that marking as read multiple times doesn't change timestamp"""
        user_alert = UserAlert.objects.create(
            user=self.user,
            alert=self.alert
        )
        
        user_alert.mark_as_read()
        first_read_time = user_alert.read_at
        
        # Mark as read again
        user_alert.mark_as_read()
        user_alert.refresh_from_db()
        
        # Timestamp should remain the same
        self.assertEqual(user_alert.read_at, first_read_time)
    
    def test_mark_as_dismissed_idempotent(self):
        """Test that marking as dismissed multiple times doesn't change timestamp"""
        user_alert = UserAlert.objects.create(
            user=self.user,
            alert=self.alert
        )
        
        user_alert.mark_as_dismissed()
        first_dismissed_time = user_alert.dismissed_at
        
        # Mark as dismissed again
        user_alert.mark_as_dismissed()
        user_alert.refresh_from_db()
        
        # Timestamp should remain the same
        self.assertEqual(user_alert.dismissed_at, first_dismissed_time)
