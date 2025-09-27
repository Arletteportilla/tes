"""
Integration tests for automatic alert generation workflow.
Tests the end-to-end process of alert generation, scheduling, and delivery.
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from factories import (
    PolinizadorUserFactory, GerminadorUserFactory, AdministradorUserFactory,
    SelfPollinationRecordFactory, GerminationRecordFactory,
    AlertTypeFactory, AlertFactory, UserAlertFactory
)
from alerts.models import Alert, UserAlert, AlertType
from alerts.services import AlertGeneratorService, NotificationService
from alerts.tasks import process_scheduled_alerts, generate_daily_alerts
from pollination.models import PollinationRecord
from germination.models import GerminationRecord

User = get_user_model()


@pytest.mark.django_db
class TestAlertsWorkflowIntegration(TransactionTestCase):
    """Test complete alerts workflow integration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.polinizador = PolinizadorUserFactory()
        self.germinador = GerminadorUserFactory()
        self.admin = AdministradorUserFactory()
        
        # Create alert types
        self.weekly_type = AlertTypeFactory(name='semanal')
        self.preventive_type = AlertTypeFactory(name='preventiva')
        self.frequent_type = AlertTypeFactory(name='frecuente')
        
        self.alert_service = AlertGeneratorService()
        self.notification_service = NotificationService()

    def test_complete_alert_generation_workflow_pollination(self):
        """Test complete alert generation workflow for pollination records."""
        # Step 1: Create pollination record
        pollination = SelfPollinationRecordFactory(responsible=self.polinizador)
        
        # Step 2: Generate weekly alert (simulating signal trigger)
        self.alert_service.generate_weekly_alert(pollination)
        
        # Verify weekly alert creation
        weekly_alerts = Alert.objects.filter(
            pollination_record=pollination,
            alert_type=self.weekly_type
        )
        self.assertEqual(weekly_alerts.count(), 1)
        
        weekly_alert = weekly_alerts.first()
        self.assertEqual(weekly_alert.status, 'pending')
        self.assertEqual(weekly_alert.priority, 'medium')
        
        # Verify scheduled date (1 week after pollination)
        expected_date = pollination.pollination_date + timedelta(days=7)
        self.assertEqual(weekly_alert.scheduled_date.date(), expected_date)
        
        # Step 3: Generate preventive alert
        self.alert_service.generate_preventive_alert(pollination)
        
        preventive_alerts = Alert.objects.filter(
            pollination_record=pollination,
            alert_type=self.preventive_type
        )
        self.assertEqual(preventive_alerts.count(), 1)
        
        preventive_alert = preventive_alerts.first()
        self.assertEqual(preventive_alert.priority, 'high')
        
        # Verify scheduled date (1 week before maturation)
        expected_preventive_date = pollination.estimated_maturation_date - timedelta(days=7)
        self.assertEqual(preventive_alert.scheduled_date.date(), expected_preventive_date)
        
        # Step 4: Verify user alert creation
        user_alerts = UserAlert.objects.filter(user=self.polinizador)
        self.assertGreaterEqual(user_alerts.count(), 2)
        
        # Step 5: Test alert API access
        self.client.force_authenticate(user=self.polinizador)
        response = self.client.get('/api/alerts/user-alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_complete_alert_generation_workflow_germination(self):
        """Test complete alert generation workflow for germination records."""
        # Step 1: Create germination record
        germination = GerminationRecordFactory(responsible=self.germinador)
        
        # Step 2: Generate weekly alert
        self.alert_service.generate_weekly_alert_germination(germination)
        
        weekly_alerts = Alert.objects.filter(
            germination_record=germination,
            alert_type=self.weekly_type
        )
        self.assertEqual(weekly_alerts.count(), 1)
        
        # Step 3: Generate preventive alert
        self.alert_service.generate_preventive_alert_germination(germination)
        
        preventive_alerts = Alert.objects.filter(
            germination_record=germination,
            alert_type=self.preventive_type
        )
        self.assertEqual(preventive_alerts.count(), 1)
        
        # Verify scheduled date for transplant
        preventive_alert = preventive_alerts.first()
        expected_date = germination.estimated_transplant_date - timedelta(days=7)
        self.assertEqual(preventive_alert.scheduled_date.date(), expected_date)

    def test_alert_workflow_with_frequent_alerts(self):
        """Test alert workflow with frequent alerts during critical periods."""
        # Step 1: Create pollination record near maturation
        past_date = date.today() - timedelta(days=113)  # 7 days before maturation (120 days)
        pollination = SelfPollinationRecordFactory(
            responsible=self.polinizador,
            pollination_date=past_date
        )
        
        # Step 2: Generate frequent alerts (daily during maturation week)
        self.alert_service.generate_frequent_alerts(pollination)
        
        frequent_alerts = Alert.objects.filter(
            pollination_record=pollination,
            alert_type=self.frequent_type
        )
        self.assertGreater(frequent_alerts.count(), 0)
        
        # Verify frequent alert properties
        frequent_alert = frequent_alerts.first()
        self.assertEqual(frequent_alert.priority, 'urgent')
        self.assertEqual(frequent_alert.status, 'pending')

    def test_alert_workflow_notification_delivery(self):
        """Test alert workflow with notification delivery."""
        # Step 1: Create alerts for different users
        pollination1 = SelfPollinationRecordFactory(responsible=self.polinizador)
        pollination2 = SelfPollinationRecordFactory(responsible=self.germinador)
        
        self.alert_service.generate_weekly_alert(pollination1)
        self.alert_service.generate_weekly_alert(pollination2)
        
        # Step 2: Test notification service
        pending_alerts = Alert.objects.filter(status='pending')
        self.assertGreaterEqual(pending_alerts.count(), 2)
        
        # Step 3: Process notifications
        for alert in pending_alerts:
            user_alerts = UserAlert.objects.filter(alert=alert)
            for user_alert in user_alerts:
                # Simulate notification delivery
                self.notification_service.send_in_app_notification(user_alert)
                
                # Verify notification was processed
                user_alert.refresh_from_db()
                self.assertIsNotNone(user_alert.created_at)

    def test_alert_workflow_with_celery_tasks(self):
        """Test alert workflow with Celery task processing."""
        # Step 1: Create multiple records that should generate alerts
        pollinations = [
            SelfPollinationRecordFactory(responsible=self.polinizador) for _ in range(3)
        ]
        germinations = [
            GerminationRecordFactory(responsible=self.germinador) for _ in range(2)
        ]
        
        # Step 2: Generate alerts for all records
        for pollination in pollinations:
            self.alert_service.generate_weekly_alert(pollination)
            self.alert_service.generate_preventive_alert(pollination)
        
        for germination in germinations:
            self.alert_service.generate_weekly_alert_germination(germination)
            self.alert_service.generate_preventive_alert_germination(germination)
        
        # Step 3: Test scheduled alert processing (simulating Celery task)
        scheduled_alerts = Alert.objects.filter(
            scheduled_date__lte=timezone.now() + timedelta(days=1),
            status='pending'
        )
        
        initial_count = scheduled_alerts.count()
        self.assertGreater(initial_count, 0)
        
        # Simulate task execution
        with patch('alerts.tasks.process_scheduled_alerts.delay') as mock_task:
            # This would normally be called by Celery beat
            process_scheduled_alerts()
            
            # Verify task was called (in real scenario)
            # For testing, we'll process directly
            for alert in scheduled_alerts:
                if alert.scheduled_date <= timezone.now():
                    alert.status = 'sent'
                    alert.save()

    def test_alert_workflow_user_interactions(self):
        """Test alert workflow with user interactions (read, dismiss)."""
        # Step 1: Create alerts for user
        self.client.force_authenticate(user=self.polinizador)
        
        pollination = SelfPollinationRecordFactory(responsible=self.polinizador)
        self.alert_service.generate_weekly_alert(pollination)
        
        # Step 2: Get user alerts via API
        response = self.client.get('/api/alerts/user-alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        
        alert_id = response.data[0]['alert']['id']
        
        # Step 3: Mark alert as read
        read_response = self.client.post(f'/api/alerts/{alert_id}/mark-read/')
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        
        # Verify alert is marked as read
        user_alert = UserAlert.objects.filter(
            user=self.polinizador,
            alert_id=alert_id
        ).first()
        self.assertTrue(user_alert.is_read)
        self.assertIsNotNone(user_alert.read_at)
        
        # Step 4: Dismiss alert
        dismiss_response = self.client.post(f'/api/alerts/{alert_id}/dismiss/')
        self.assertEqual(dismiss_response.status_code, status.HTTP_200_OK)
        
        # Verify alert is dismissed
        user_alert.refresh_from_db()
        self.assertTrue(user_alert.is_dismissed)
        self.assertIsNotNone(user_alert.dismissed_at)

    def test_alert_workflow_bulk_operations(self):
        """Test alert workflow with bulk operations."""
        # Step 1: Create multiple alerts for user
        pollinations = [
            SelfPollinationRecordFactory(responsible=self.polinizador) for _ in range(5)
        ]
        
        for pollination in pollinations:
            self.alert_service.generate_weekly_alert(pollination)
        
        # Step 2: Test bulk mark as read
        self.client.force_authenticate(user=self.polinizador)
        
        response = self.client.get('/api/alerts/user-alerts/')
        alert_ids = [alert['alert']['id'] for alert in response.data]
        
        bulk_read_data = {'alert_ids': alert_ids[:3]}  # Mark first 3 as read
        bulk_response = self.client.post('/api/alerts/bulk-mark-read/', bulk_read_data)
        self.assertEqual(bulk_response.status_code, status.HTTP_200_OK)
        
        # Verify bulk operation
        read_alerts = UserAlert.objects.filter(
            user=self.polinizador,
            alert_id__in=alert_ids[:3],
            is_read=True
        )
        self.assertEqual(read_alerts.count(), 3)

    def test_alert_workflow_filtering_and_pagination(self):
        """Test alert workflow with filtering and pagination."""
        # Step 1: Create alerts of different types and priorities
        pollination = SelfPollinationRecordFactory(responsible=self.polinizador)
        germination = GerminationRecordFactory(responsible=self.polinizador)
        
        # Generate different types of alerts
        self.alert_service.generate_weekly_alert(pollination)
        self.alert_service.generate_preventive_alert(pollination)
        self.alert_service.generate_weekly_alert_germination(germination)
        
        self.client.force_authenticate(user=self.polinizador)
        
        # Step 2: Test filtering by alert type
        response = self.client.get('/api/alerts/user-alerts/?alert_type=semanal')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # All returned alerts should be weekly
        for alert_data in response.data:
            self.assertEqual(alert_data['alert']['alert_type']['name'], 'semanal')
        
        # Step 3: Test filtering by priority
        response = self.client.get('/api/alerts/user-alerts/?priority=high')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 4: Test filtering by status
        # First mark some alerts as read
        all_alerts_response = self.client.get('/api/alerts/user-alerts/')
        if all_alerts_response.data:
            alert_id = all_alerts_response.data[0]['alert']['id']
            self.client.post(f'/api/alerts/{alert_id}/mark-read/')
        
        # Filter by unread status
        unread_response = self.client.get('/api/alerts/user-alerts/?is_read=false')
        read_response = self.client.get('/api/alerts/user-alerts/?is_read=true')
        
        self.assertEqual(unread_response.status_code, status.HTTP_200_OK)
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)

    def test_alert_workflow_error_handling(self):
        """Test alert workflow error handling."""
        # Step 1: Test alert generation with invalid data
        with self.assertRaises(Exception):
            self.alert_service.generate_weekly_alert(None)
        
        # Step 2: Test API error handling
        self.client.force_authenticate(user=self.polinizador)
        
        # Try to access non-existent alert
        response = self.client.post('/api/alerts/99999/mark-read/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Step 3: Test unauthorized access
        unauthorized_client = APIClient()
        response = unauthorized_client.get('/api/alerts/user-alerts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Step 4: Test access to other user's alerts
        other_user = PolinizadorUserFactory()
        other_pollination = SelfPollinationRecordFactory(responsible=other_user)
        self.alert_service.generate_weekly_alert(other_pollination)
        
        # Current user should not see other user's alerts
        response = self.client.get('/api/alerts/user-alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify no alerts from other user are returned
        for alert_data in response.data:
            user_alert = UserAlert.objects.get(id=alert_data['id'])
            self.assertEqual(user_alert.user, self.polinizador)

    def test_alert_workflow_performance_with_large_dataset(self):
        """Test alert workflow performance with large dataset."""
        # Step 1: Create large number of records
        pollinations = [
            SelfPollinationRecordFactory(responsible=self.polinizador) for _ in range(50)
        ]
        germinations = [
            GerminationRecordFactory(responsible=self.polinizador) for _ in range(30)
        ]
        
        # Step 2: Generate alerts in batch
        import time
        start_time = time.time()
        
        for pollination in pollinations:
            self.alert_service.generate_weekly_alert(pollination)
        
        for germination in germinations:
            self.alert_service.generate_weekly_alert_germination(germination)
        
        generation_time = time.time() - start_time
        
        # Step 3: Test API performance
        self.client.force_authenticate(user=self.polinizador)
        
        start_time = time.time()
        response = self.client.get('/api/alerts/user-alerts/')
        api_time = time.time() - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify reasonable performance (adjust thresholds as needed)
        self.assertLess(generation_time, 10.0)  # Alert generation should be under 10 seconds
        self.assertLess(api_time, 2.0)  # API response should be under 2 seconds
        
        # Verify all alerts were created
        total_alerts = Alert.objects.filter(
            useralert__user=self.polinizador
        ).count()
        self.assertEqual(total_alerts, 80)  # 50 + 30 alerts