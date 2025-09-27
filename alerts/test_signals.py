from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from alerts.models import Alert, UserAlert
from authentication.models import Role
from pollination.models import PollinationRecord, Plant, PollinationType, ClimateCondition
from germination.models import GerminationRecord, SeedSource, GerminationCondition

User = get_user_model()


class AlertSignalsTest(TestCase):
    """Test cases for alert generation signals"""
    
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
    
    def test_pollination_record_creates_alerts(self):
        """Test that creating a pollination record automatically creates alerts"""
        # Count alerts before creating record
        initial_alert_count = Alert.objects.count()
        initial_user_alert_count = UserAlert.objects.count()
        
        # Create pollination record (this should trigger the signal)
        pollination_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        # Check that alerts were created
        final_alert_count = Alert.objects.count()
        final_user_alert_count = UserAlert.objects.count()
        
        # Should have created multiple alerts (weekly + preventive + frequent)
        self.assertGreater(final_alert_count, initial_alert_count)
        self.assertGreater(final_user_alert_count, initial_user_alert_count)
        
        # Check that alerts are related to the pollination record
        pollination_alerts = Alert.objects.filter(pollination_record=pollination_record)
        self.assertGreater(pollination_alerts.count(), 0)
        
        # Check that user alerts were created for the responsible user
        user_alerts = UserAlert.objects.filter(
            user=self.user,
            alert__pollination_record=pollination_record
        )
        self.assertGreater(user_alerts.count(), 0)
    
    def test_germination_record_creates_alerts(self):
        """Test that creating a germination record automatically creates alerts"""
        # Count alerts before creating record
        initial_alert_count = Alert.objects.count()
        initial_user_alert_count = UserAlert.objects.count()
        
        # Create germination record (this should trigger the signal)
        germination_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today(),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
        
        # Check that alerts were created
        final_alert_count = Alert.objects.count()
        final_user_alert_count = UserAlert.objects.count()
        
        # Should have created multiple alerts (weekly + preventive + frequent)
        self.assertGreater(final_alert_count, initial_alert_count)
        self.assertGreater(final_user_alert_count, initial_user_alert_count)
        
        # Check that alerts are related to the germination record
        germination_alerts = Alert.objects.filter(germination_record=germination_record)
        self.assertGreater(germination_alerts.count(), 0)
        
        # Check that user alerts were created for the responsible user
        user_alerts = UserAlert.objects.filter(
            user=self.user,
            alert__germination_record=germination_record
        )
        self.assertGreater(user_alerts.count(), 0)
    
    def test_updating_record_does_not_create_duplicate_alerts(self):
        """Test that updating a record doesn't create duplicate alerts"""
        # Create pollination record
        pollination_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        # Count alerts after creation
        alert_count_after_creation = Alert.objects.filter(
            pollination_record=pollination_record
        ).count()
        
        # Update the record
        pollination_record.observations = 'Updated observations'
        pollination_record.save()
        
        # Count alerts after update
        alert_count_after_update = Alert.objects.filter(
            pollination_record=pollination_record
        ).count()
        
        # Alert count should remain the same
        self.assertEqual(alert_count_after_creation, alert_count_after_update)
    
    def test_multiple_users_get_separate_alerts(self):
        """Test that different users get separate alert instances"""
        # Create second user
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create records for different users
        pollination_record1 = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        pollination_record2 = PollinationRecord.objects.create(
            responsible=user2,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=3
        )
        
        # Check that each user has their own alerts
        user1_alerts = UserAlert.objects.filter(
            user=self.user,
            alert__pollination_record=pollination_record1
        )
        
        user2_alerts = UserAlert.objects.filter(
            user=user2,
            alert__pollination_record=pollination_record2
        )
        
        self.assertGreater(user1_alerts.count(), 0)
        self.assertGreater(user2_alerts.count(), 0)
        
        # Check that users don't have alerts for other users' records
        user1_alerts_for_user2_record = UserAlert.objects.filter(
            user=self.user,
            alert__pollination_record=pollination_record2
        )
        
        user2_alerts_for_user1_record = UserAlert.objects.filter(
            user=user2,
            alert__pollination_record=pollination_record1
        )
        
        self.assertEqual(user1_alerts_for_user2_record.count(), 0)
        self.assertEqual(user2_alerts_for_user1_record.count(), 0)