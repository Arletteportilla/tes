from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from alerts.models import AlertType, Alert, UserAlert
from alerts.services import AlertGeneratorService
from authentication.models import Role
from pollination.models import PollinationRecord, Plant, PollinationType, ClimateCondition
from germination.models import GerminationRecord, SeedSource, GerminationCondition

User = get_user_model()


class AlertGeneratorServiceTest(TestCase):
    """Test cases for AlertGeneratorService"""
    
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
        
        # Create alert types
        self.weekly_alert_type = AlertType.objects.create(
            name='semanal',
            description='Weekly alert'
        )
        self.preventive_alert_type = AlertType.objects.create(
            name='preventiva',
            description='Preventive alert'
        )
        self.frequent_alert_type = AlertType.objects.create(
            name='frecuente',
            description='Frequent alert'
        )
        
        # Create test data for pollination
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
            pollination_date=date.today(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        # Create test data for germination
        self.seed_source = SeedSource.objects.create(
            name='Test Source',
            source_type='autopolinización'
        )
        
        self.germination_condition = GerminationCondition.objects.create(
            substrate='Test Substrate',
            temperature=22.0,
            humidity=70
        )
        
        self.germination_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
    
    def test_create_weekly_alert_pollination(self):
        """Test creating weekly alert for pollination record"""
        alert = AlertGeneratorService.create_weekly_alert(
            self.pollination_record, 
            'pollination'
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, self.weekly_alert_type)
        self.assertEqual(alert.pollination_record, self.pollination_record)
        self.assertEqual(alert.priority, 'medium')
        self.assertEqual(alert.status, 'pending')
        
        # Check that scheduled date is one week after creation
        expected_date = self.pollination_record.created_at + timedelta(days=7)
        self.assertEqual(alert.scheduled_date.date(), expected_date.date())
        
        # Check that user alert was created
        user_alert = UserAlert.objects.get(alert=alert, user=self.user)
        self.assertIsNotNone(user_alert)
        self.assertFalse(user_alert.is_read)
    
    def test_create_weekly_alert_germination(self):
        """Test creating weekly alert for germination record"""
        alert = AlertGeneratorService.create_weekly_alert(
            self.germination_record, 
            'germination'
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, self.weekly_alert_type)
        self.assertEqual(alert.germination_record, self.germination_record)
        self.assertEqual(alert.priority, 'medium')
        
        # Check that user alert was created
        user_alert = UserAlert.objects.get(alert=alert, user=self.user)
        self.assertIsNotNone(user_alert)
    
    def test_create_preventive_alert_pollination(self):
        """Test creating preventive alert for pollination record"""
        alert = AlertGeneratorService.create_preventive_alert(
            self.pollination_record, 
            'pollination'
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, self.preventive_alert_type)
        self.assertEqual(alert.pollination_record, self.pollination_record)
        self.assertEqual(alert.priority, 'high')
        
        # Check that scheduled date is one week before estimated maturation
        expected_date = self.pollination_record.estimated_maturation_date - timedelta(days=7)
        self.assertEqual(alert.scheduled_date.date(), expected_date)
    
    def test_create_preventive_alert_germination(self):
        """Test creating preventive alert for germination record"""
        alert = AlertGeneratorService.create_preventive_alert(
            self.germination_record, 
            'germination'
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, self.preventive_alert_type)
        self.assertEqual(alert.germination_record, self.germination_record)
        self.assertEqual(alert.priority, 'high')
    
    def test_create_frequent_alerts_pollination(self):
        """Test creating frequent alerts for pollination record"""
        alerts = AlertGeneratorService.create_frequent_alerts(
            self.pollination_record, 
            'pollination'
        )
        
        # Should create 7 alerts (3 days before, day of, 3 days after)
        self.assertEqual(len(alerts), 7)
        
        # Check that all alerts are of frequent type
        for alert in alerts:
            self.assertEqual(alert.alert_type, self.frequent_alert_type)
            self.assertEqual(alert.pollination_record, self.pollination_record)
        
        # Check priorities
        urgent_alerts = [a for a in alerts if a.priority == 'urgent']
        high_alerts = [a for a in alerts if a.priority == 'high']
        
        # Should have 1 urgent (day of) + 3 urgent (overdue) = 4 urgent
        # Should have 3 high (before) = 3 high
        self.assertEqual(len(urgent_alerts), 4)
        self.assertEqual(len(high_alerts), 3)
    
    def test_create_frequent_alerts_germination(self):
        """Test creating frequent alerts for germination record"""
        alerts = AlertGeneratorService.create_frequent_alerts(
            self.germination_record, 
            'germination'
        )
        
        # Should create 7 alerts
        self.assertEqual(len(alerts), 7)
        
        # Check that all alerts are of frequent type
        for alert in alerts:
            self.assertEqual(alert.alert_type, self.frequent_alert_type)
            self.assertEqual(alert.germination_record, self.germination_record)
    
    def test_generate_all_alerts_for_record_pollination(self):
        """Test generating all alert types for pollination record"""
        alerts = AlertGeneratorService.generate_all_alerts_for_record(
            self.pollination_record, 
            'pollination'
        )
        
        # Should create 1 weekly + 1 preventive + 7 frequent = 9 alerts
        self.assertEqual(len(alerts), 9)
        
        # Check alert types distribution
        weekly_alerts = [a for a in alerts if a.alert_type.name == 'semanal']
        preventive_alerts = [a for a in alerts if a.alert_type.name == 'preventiva']
        frequent_alerts = [a for a in alerts if a.alert_type.name == 'frecuente']
        
        self.assertEqual(len(weekly_alerts), 1)
        self.assertEqual(len(preventive_alerts), 1)
        self.assertEqual(len(frequent_alerts), 7)
    
    def test_generate_all_alerts_for_record_germination(self):
        """Test generating all alert types for germination record"""
        alerts = AlertGeneratorService.generate_all_alerts_for_record(
            self.germination_record, 
            'germination'
        )
        
        # Should create 1 weekly + 1 preventive + 7 frequent = 9 alerts
        self.assertEqual(len(alerts), 9)
    
    def test_cleanup_expired_alerts(self):
        """Test cleanup of expired alerts"""
        # Create an expired alert
        expired_alert = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Expired Alert',
            message='This alert has expired',
            scheduled_date=timezone.now(),
            expires_at=timezone.now() - timedelta(hours=1),
            status='pending'
        )
        
        # Create a non-expired alert
        active_alert = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Active Alert',
            message='This alert is still active',
            scheduled_date=timezone.now(),
            expires_at=timezone.now() + timedelta(hours=1),
            status='pending'
        )
        
        # Run cleanup
        expired_count = AlertGeneratorService.cleanup_expired_alerts()
        
        # Check results
        self.assertEqual(expired_count, 1)
        
        expired_alert.refresh_from_db()
        active_alert.refresh_from_db()
        
        self.assertEqual(expired_alert.status, 'dismissed')
        self.assertEqual(active_alert.status, 'pending')
    
    def test_get_pending_alerts_for_user(self):
        """Test getting pending alerts for a user"""
        # Clear existing alerts from setUp (created by signals)
        UserAlert.objects.filter(user=self.user).delete()
        Alert.objects.all().delete()
        
        # Create alerts for the user
        alert1 = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Alert 1',
            message='Message 1',
            scheduled_date=timezone.now(),
            status='pending'
        )
        
        alert2 = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Alert 2',
            message='Message 2',
            scheduled_date=timezone.now(),
            status='pending'
        )
        
        # Create user alerts
        user_alert1 = UserAlert.objects.create(user=self.user, alert=alert1)
        user_alert2 = UserAlert.objects.create(user=self.user, alert=alert2)
        
        # Mark one as read
        user_alert1.mark_as_read()
        
        # Get pending alerts
        pending_alerts = AlertGeneratorService.get_pending_alerts_for_user(self.user)
        
        # Should only return the unread alert
        self.assertEqual(pending_alerts.count(), 1)
        self.assertEqual(pending_alerts.first().alert, alert2)
    
    def test_get_alerts_due_today(self):
        """Test getting alerts due today"""
        # Clear existing alerts from setUp (created by signals)
        Alert.objects.all().delete()
        
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Create alert due today
        today_alert = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Today Alert',
            message='Due today',
            scheduled_date=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.min.time())
            ),
            status='pending'
        )
        
        # Create alert due tomorrow
        tomorrow_alert = Alert.objects.create(
            alert_type=self.weekly_alert_type,
            title='Tomorrow Alert',
            message='Due tomorrow',
            scheduled_date=timezone.make_aware(
                timezone.datetime.combine(tomorrow, timezone.datetime.min.time())
            ),
            status='pending'
        )
        
        # Get alerts due today
        due_today = AlertGeneratorService.get_alerts_due_today()
        
        # Should only return today's alert
        self.assertEqual(due_today.count(), 1)
        self.assertEqual(due_today.first(), today_alert)