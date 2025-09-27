from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta, date

from alerts.models import Alert, AlertType, UserAlert
from alerts.services import NotificationService
from authentication.models import Role
from pollination.models import PollinationRecord, Plant, PollinationType, ClimateCondition

User = get_user_model()


class AlertViewSetTest(TestCase):
    """Test cases for AlertViewSet"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test users and roles
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Administrator role'
        )
        self.user_role = Role.objects.create(
            name='Polinizador',
            description='Pollinator role'
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123',
            role=self.user_role
        )
        
        # Create alert type
        self.alert_type = AlertType.objects.create(
            name='semanal',
            description='Weekly alert'
        )
        
        # Create test alert
        self.alert = Alert.objects.create(
            alert_type=self.alert_type,
            title='Test Alert',
            message='Test message',
            scheduled_date=timezone.now(),
            priority='medium'
        )
        
        # Create user alert for regular user
        self.user_alert = UserAlert.objects.create(
            user=self.regular_user,
            alert=self.alert
        )
    
    def test_alert_list_requires_authentication(self):
        """Test that alert list requires authentication"""
        url = reverse('alerts:alert-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_regular_user_sees_only_own_alerts(self):
        """Test that regular users only see their own alerts"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('alerts:alert-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.alert.id)
    
    def test_admin_user_sees_all_alerts(self):
        """Test that admin users see all alerts"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('alerts:alert-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_mark_alert_as_read(self):
        """Test marking an alert as read"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('alerts:alert-mark-as-read', kwargs={'pk': self.alert.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_alert.refresh_from_db()
        self.assertTrue(self.user_alert.is_read)
    
    def test_mark_alert_as_dismissed(self):
        """Test marking an alert as dismissed"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('alerts:alert-mark-as-dismissed', kwargs={'pk': self.alert.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_alert.refresh_from_db()
        self.assertTrue(self.user_alert.is_dismissed)


class NotificationViewSetTest(TestCase):
    """Test cases for NotificationViewSet"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user and role
        self.role = Role.objects.create(
            name='Polinizador',
            description='Pollinator role'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create alert types
        self.weekly_alert_type = AlertType.objects.create(
            name='semanal',
            description='Weekly alert'
        )
        self.urgent_alert_type = AlertType.objects.create(
            name='frecuente',
            description='Frequent alert'
        )
        
        # Create test alerts
        self.alert1 = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Weekly Alert',
            message='Weekly message',
            scheduled_date=timezone.now(),
            priority='medium'
        )
        
        self.alert2 = Alert.objects.create(
            alert_type=self.urgent_alert_type,
            title='Urgent Alert',
            message='Urgent message',
            scheduled_date=timezone.now(),
            priority='urgent'
        )
        
        # Create user alerts
        self.user_alert1 = UserAlert.objects.create(
            user=self.user,
            alert=self.alert1
        )
        
        self.user_alert2 = UserAlert.objects.create(
            user=self.user,
            alert=self.alert2
        )
    
    def test_notification_list_requires_authentication(self):
        """Test that notification list requires authentication"""
        url = reverse('alerts:notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_sees_own_notifications(self):
        """Test that users see their own notifications"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_notification_summary(self):
        """Test notification summary endpoint"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_notifications'], 2)
        self.assertEqual(response.data['unread_notifications'], 2)
        self.assertEqual(response.data['urgent_notifications'], 1)
        self.assertTrue(response.data['has_unread'])
        self.assertTrue(response.data['has_urgent'])
    
    def test_unread_notifications(self):
        """Test unread notifications endpoint"""
        # Mark one notification as read
        self.user_alert1.mark_as_read()
        
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-unread')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.user_alert2.id)
    
    def test_notifications_by_type(self):
        """Test filtering notifications by type"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-by-type')
        response = self.client.get(url, {'type': 'semanal'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['alert']['alert_type_name'], 'semanal')
    
    def test_notifications_by_priority(self):
        """Test filtering notifications by priority"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-by-priority')
        response = self.client.get(url, {'priority': 'urgent'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['alert']['priority'], 'urgent')
    
    def test_mark_notification_as_read(self):
        """Test marking a notification as read"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-mark-as-read', kwargs={'pk': self.user_alert1.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_alert1.refresh_from_db()
        self.assertTrue(self.user_alert1.is_read)
    
    def test_mark_notification_as_dismissed(self):
        """Test marking a notification as dismissed"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-mark-as-dismissed', kwargs={'pk': self.user_alert1.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_alert1.refresh_from_db()
        self.assertTrue(self.user_alert1.is_dismissed)
    
    def test_mark_all_notifications_as_read(self):
        """Test marking all notifications as read"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-mark-all-as-read')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that both notifications are marked as read
        self.user_alert1.refresh_from_db()
        self.user_alert2.refresh_from_db()
        self.assertTrue(self.user_alert1.is_read)
        self.assertTrue(self.user_alert2.is_read)
    
    def test_bulk_action_mark_all_read(self):
        """Test bulk action to mark all notifications as read"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-bulk-action')
        data = {'action': 'mark_all_read'}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that both notifications are marked as read
        self.user_alert1.refresh_from_db()
        self.user_alert2.refresh_from_db()
        self.assertTrue(self.user_alert1.is_read)
        self.assertTrue(self.user_alert2.is_read)
    
    def test_bulk_action_dismiss_all_read(self):
        """Test bulk action to dismiss all read notifications"""
        # First mark notifications as read
        self.user_alert1.mark_as_read()
        self.user_alert2.mark_as_read()
        
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-bulk-action')
        data = {'action': 'dismiss_all_read'}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that both notifications are dismissed
        self.user_alert1.refresh_from_db()
        self.user_alert2.refresh_from_db()
        self.assertTrue(self.user_alert1.is_dismissed)
        self.assertTrue(self.user_alert2.is_dismissed)
    
    def test_cleanup_old_notifications(self):
        """Test cleaning up old notifications"""
        # Create an old notification
        old_alert = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Old Alert',
            message='Old message',
            scheduled_date=timezone.now() - timedelta(days=35),
            priority='low'
        )
        old_user_alert = UserAlert.objects.create(
            user=self.user,
            alert=old_alert,
            is_read=True
        )
        # Manually set the created_at to be old
        old_user_alert.created_at = timezone.now() - timedelta(days=35)
        old_user_alert.save()
        
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:notification-cleanup-old')
        data = {'days_old': 30}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that old notification was cleaned up
        self.assertFalse(UserAlert.objects.filter(id=old_user_alert.id).exists())


class AlertTypeViewSetTest(TestCase):
    """Test cases for AlertTypeViewSet"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user and role
        self.role = Role.objects.create(
            name='Polinizador',
            description='Pollinator role'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create alert types
        self.alert_type1 = AlertType.objects.create(
            name='semanal',
            description='Weekly alert'
        )
        self.alert_type2 = AlertType.objects.create(
            name='preventiva',
            description='Preventive alert'
        )
    
    def test_alert_type_list_requires_authentication(self):
        """Test that alert type list requires authentication"""
        url = reverse('alerts:alerttype-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_authenticated_user_can_list_alert_types(self):
        """Test that authenticated users can list alert types"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:alerttype-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_alert_type_detail(self):
        """Test alert type detail endpoint"""
        self.client.force_authenticate(user=self.user)
        url = reverse('alerts:alerttype-detail', kwargs={'pk': self.alert_type1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'semanal')
        self.assertEqual(response.data['description'], 'Weekly alert')