import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from factories import (
    RoleFactory, CustomUserFactory, UserProfileFactory,
    PlantFactory, OrchidPlantFactory, PollinationTypeFactory, ClimateConditionFactory,
    SelfPollinationRecordFactory, SiblingPollinationRecordFactory, HybridPollinationRecordFactory,
    SeedSourceFactory, GerminationSetupFactory, GerminationRecordFactory,
    AlertTypeFactory, PollinationAlertFactory, GerminationAlertFactory, UserAlertFactory,
    ReportTypeFactory, CompletedReportFactory, PollinationReportFactory
)
from authentication.models import Role, UserProfile
from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
from germination.models import SeedSource, GerminationSetup, GerminationRecord
from alerts.models import AlertType, Alert, UserAlert
from reports.models import ReportType, Report

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationFactories(TestCase):
    """Test authentication-related factories."""

    def test_role_factory(self):
        """Test RoleFactory creates valid roles."""
        role = RoleFactory()
        self.assertIsInstance(role, Role)
        self.assertIn(role.name, ['Polinizador', 'Germinador', 'Secretaria', 'Administrador'])
        self.assertTrue(role.is_active)
        self.assertIsInstance(role.permissions, dict)

    def test_custom_user_factory(self):
        """Test CustomUserFactory creates valid users."""
        user = CustomUserFactory()
        self.assertIsInstance(user, User)
        self.assertTrue(user.username)
        self.assertTrue(user.email)
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.role)
        self.assertTrue(user.check_password('testpass123'))

    def test_user_profile_factory(self):
        """Test UserProfileFactory creates valid profiles."""
        profile = UserProfileFactory()
        self.assertIsInstance(profile, UserProfile)
        self.assertIsNotNone(profile.user)
        self.assertIsInstance(profile.preferences, dict)

    def test_role_specific_user_factories(self):
        """Test role-specific user factories."""
        from factories import PolinizadorUserFactory, GerminadorUserFactory, SecretariaUserFactory, AdministradorUserFactory
        
        polinizador = PolinizadorUserFactory()
        self.assertEqual(polinizador.role.name, 'Polinizador')
        
        germinador = GerminadorUserFactory()
        self.assertEqual(germinador.role.name, 'Germinador')
        
        secretaria = SecretariaUserFactory()
        self.assertEqual(secretaria.role.name, 'Secretaria')
        
        admin = AdministradorUserFactory()
        self.assertEqual(admin.role.name, 'Administrador')


@pytest.mark.django_db
class TestPollinationFactories(TestCase):
    """Test pollination-related factories."""

    def test_plant_factory(self):
        """Test PlantFactory creates valid plants."""
        plant = PlantFactory()
        self.assertIsInstance(plant, Plant)
        self.assertTrue(plant.genus)
        self.assertTrue(plant.species)
        self.assertTrue(plant.vivero)
        self.assertTrue(plant.mesa)
        self.assertTrue(plant.pared)
        self.assertTrue(plant.is_active)

    def test_orchid_plant_factory(self):
        """Test OrchidPlantFactory creates realistic orchid plants."""
        orchid = OrchidPlantFactory()
        self.assertIsInstance(orchid, Plant)
        self.assertIn(orchid.genus, ['Cattleya', 'Phalaenopsis', 'Dendrobium', 'Oncidium'])
        self.assertIn(orchid.species, ['trianae', 'amabilis', 'nobile', 'flexuosum'])

    def test_pollination_type_factory(self):
        """Test PollinationTypeFactory creates valid types."""
        poll_type = PollinationTypeFactory()
        self.assertIsInstance(poll_type, PollinationType)
        self.assertIn(poll_type.name, ['Self', 'Sibling', 'Híbrido'])
        self.assertEqual(poll_type.maturation_days, 120)

    def test_climate_condition_factory(self):
        """Test ClimateConditionFactory creates valid conditions."""
        climate = ClimateConditionFactory()
        self.assertIsInstance(climate, ClimateCondition)
        self.assertIn(climate.weather, ['Soleado', 'Nublado', 'Lluvioso', 'Parcialmente nublado'])
        self.assertIsNotNone(climate.temperature)
        self.assertIsNotNone(climate.humidity)

    def test_pollination_record_factory(self):
        """Test PollinationRecordFactory creates valid records."""
        record = SelfPollinationRecordFactory()
        self.assertIsInstance(record, PollinationRecord)
        self.assertIsNotNone(record.responsible)
        self.assertIsNotNone(record.pollination_type)
        self.assertIsNotNone(record.mother_plant)
        self.assertIsNotNone(record.new_plant)
        self.assertIsNotNone(record.climate_condition)
        self.assertGreater(record.capsules_quantity, 0)

    def test_self_pollination_record(self):
        """Test SelfPollinationRecordFactory creates valid self pollination."""
        record = SelfPollinationRecordFactory()
        self.assertEqual(record.pollination_type.name, 'Self')
        self.assertIsNone(record.father_plant)

    def test_sibling_pollination_record(self):
        """Test SiblingPollinationRecordFactory creates valid sibling pollination."""
        record = SiblingPollinationRecordFactory()
        self.assertEqual(record.pollination_type.name, 'Sibling')
        self.assertIsNotNone(record.father_plant)

    def test_hybrid_pollination_record(self):
        """Test HybridPollinationRecordFactory creates valid hybrid pollination."""
        record = HybridPollinationRecordFactory()
        self.assertEqual(record.pollination_type.name, 'Híbrido')
        self.assertIsNotNone(record.father_plant)


@pytest.mark.django_db
class TestGerminationFactories(TestCase):
    """Test germination-related factories."""

    def test_seed_source_factory(self):
        """Test SeedSourceFactory creates valid seed sources."""
        source = SeedSourceFactory()
        self.assertIsInstance(source, SeedSource)
        self.assertTrue(source.name)
        self.assertIn(source.source_type, ['Autopolinización', 'Sibling', 'Híbrido', 'Otra fuente'])
        self.assertTrue(source.is_active)

    def test_germination_setup_factory(self):
        """Test GerminationSetupFactory creates valid setups."""
        setup = GerminationSetupFactory()
        self.assertIsInstance(setup, GerminationSetup)
        self.assertIsNotNone(setup.climate_condition)
        self.assertIn(setup.climate_condition.climate, ['C', 'IC', 'I', 'IW', 'W'])

    def test_germination_record_factory(self):
        """Test GerminationRecordFactory creates valid records."""
        record = GerminationRecordFactory()
        self.assertIsInstance(record, GerminationRecord)
        self.assertIsNotNone(record.responsible)
        self.assertIsNotNone(record.plant)
        self.assertIsNotNone(record.seed_source)
        self.assertIsNotNone(record.germination_setup)
        self.assertGreater(record.seeds_planted, 0)
        self.assertLessEqual(record.seedlings_germinated, record.seeds_planted)


@pytest.mark.django_db
class TestAlertsFactories(TestCase):
    """Test alerts-related factories."""

    def test_alert_type_factory(self):
        """Test AlertTypeFactory creates valid alert types."""
        alert_type = AlertTypeFactory()
        self.assertIsInstance(alert_type, AlertType)
        self.assertIn(alert_type.name, ['semanal', 'preventiva', 'frecuente'])
        self.assertTrue(alert_type.is_active)

    def test_alert_factory(self):
        """Test AlertFactory creates valid alerts."""
        from factories import AlertFactory
        alert = AlertFactory()
        self.assertIsInstance(alert, Alert)
        self.assertTrue(alert.title)
        self.assertTrue(alert.message)
        self.assertIn(alert.status, ['pending', 'read', 'dismissed'])
        self.assertIn(alert.priority, ['low', 'medium', 'high', 'urgent'])

    def test_pollination_alert_factory(self):
        """Test PollinationAlertFactory creates valid pollination alerts."""
        alert = PollinationAlertFactory()
        self.assertIsInstance(alert, Alert)
        self.assertIsNotNone(alert.pollination_record)
        self.assertIn('polinización', alert.title.lower())

    def test_user_alert_factory(self):
        """Test UserAlertFactory creates valid user alerts."""
        user_alert = UserAlertFactory()
        self.assertIsInstance(user_alert, UserAlert)
        self.assertIsNotNone(user_alert.user)
        self.assertIsNotNone(user_alert.alert)


@pytest.mark.django_db
class TestReportsFactories(TestCase):
    """Test reports-related factories."""

    def test_report_type_factory(self):
        """Test ReportTypeFactory creates valid report types."""
        report_type = ReportTypeFactory()
        self.assertIsInstance(report_type, ReportType)
        self.assertIn(report_type.name, ['pollination', 'germination', 'statistical'])
        self.assertTrue(report_type.is_active)

    def test_report_factory(self):
        """Test ReportFactory creates valid reports."""
        from factories import ReportFactory
        report = ReportFactory()
        self.assertIsInstance(report, Report)
        self.assertTrue(report.title)
        self.assertIsNotNone(report.report_type)
        self.assertIsNotNone(report.generated_by)
        self.assertIn(report.format, ['pdf', 'excel', 'json'])

    def test_completed_report_factory(self):
        """Test CompletedReportFactory creates completed reports."""
        report = CompletedReportFactory()
        self.assertEqual(report.status, 'completed')
        self.assertIsNotNone(report.file_path)
        self.assertIsNotNone(report.file_size)
        self.assertIsNotNone(report.generation_started_at)
        self.assertIsNotNone(report.generation_completed_at)

    def test_pollination_report_factory(self):
        """Test PollinationReportFactory creates pollination reports."""
        report = PollinationReportFactory()
        self.assertEqual(report.report_type.name, 'pollination')
        self.assertIn('Polinización', report.title)


@pytest.mark.django_db
class TestFactoryIntegration(TestCase):
    """Test factory integration and relationships."""

    def test_create_complete_workflow(self):
        """Test creating a complete workflow using factories."""
        # Create user
        user = CustomUserFactory(role__name='Polinizador')
        
        # Create pollination record
        pollination = SelfPollinationRecordFactory(responsible=user)
        
        # Create germination record using seeds from pollination
        germination = GerminationRecordFactory(
            responsible=user,
            seed_source__pollination_record=pollination
        )
        
        # Create alerts for both records
        poll_alert = PollinationAlertFactory(pollination_record=pollination)
        germ_alert = GerminationAlertFactory(germination_record=germination)
        
        # Create user alerts
        UserAlertFactory(user=user, alert=poll_alert)
        UserAlertFactory(user=user, alert=germ_alert)
        
        # Verify relationships
        self.assertEqual(pollination.responsible, user)
        self.assertEqual(germination.responsible, user)
        self.assertEqual(poll_alert.pollination_record, pollination)
        self.assertEqual(germ_alert.germination_record, germination)
        self.assertGreaterEqual(user.user_alerts.count(), 2)  # At least 2, but may have more from signals

    def test_batch_creation(self):
        """Test creating multiple objects using factories."""
        # Create multiple users with different roles
        users = [
            CustomUserFactory(role__name='Polinizador') for _ in range(3)
        ] + [
            CustomUserFactory(role__name='Germinador') for _ in range(2)
        ]
        
        # Create multiple plants
        plants = [PlantFactory() for _ in range(10)]
        
        # Create multiple pollination records
        pollinations = [
            SelfPollinationRecordFactory(responsible=users[i % len(users)])
            for i in range(5)
        ]
        
        # Verify creation
        self.assertEqual(len(users), 5)
        self.assertEqual(len(plants), 10)
        self.assertEqual(len(pollinations), 5)
        self.assertEqual(User.objects.count(), 5)
        self.assertEqual(Plant.objects.count(), 10)
        self.assertEqual(PollinationRecord.objects.count(), 5)