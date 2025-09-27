"""
Integration tests for complete pollination workflow.
Tests the end-to-end process from pollination record creation to alert generation.
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from factories import (
    PolinizadorUserFactory, PlantFactory, PollinationTypeFactory, 
    ClimateConditionFactory, SelfPollinationRecordFactory,
    SiblingPollinationRecordFactory, HybridPollinationRecordFactory
)
from pollination.models import PollinationRecord
from alerts.models import Alert, UserAlert
from alerts.services import AlertGeneratorService
from pollination.services import PollinationService

User = get_user_model()


@pytest.mark.django_db
class TestPollinationWorkflowIntegration(TransactionTestCase):
    """Test complete pollination workflow integration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.polinizador = PolinizadorUserFactory()
        self.client.force_authenticate(user=self.polinizador)
        
        # Create required data
        self.mother_plant = PlantFactory(genus='Cattleya', species='trianae')
        self.father_plant = PlantFactory(genus='Cattleya', species='trianae')
        self.new_plant = PlantFactory(genus='Cattleya', species='trianae')
        self.climate = ClimateConditionFactory()
        
        # Create pollination types
        self.self_type = PollinationTypeFactory(name='Self')
        self.sibling_type = PollinationTypeFactory(name='Sibling')
        self.hybrid_type = PollinationTypeFactory(name='Híbrido')

    def test_complete_self_pollination_workflow(self):
        """Test complete self pollination workflow from creation to alerts."""
        # Step 1: Create self pollination record via API
        pollination_data = {
            'responsible': self.polinizador.id,
            'pollination_type': self.self_type.id,
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.mother_plant.id,
            'new_plant': self.new_plant.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 5,
            'observations': 'Test self pollination workflow'
        }
        
        response = self.client.post('/api/pollination/records/', pollination_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify record creation
        pollination_id = response.data['id']
        pollination = PollinationRecord.objects.get(id=pollination_id)
        self.assertEqual(pollination.responsible, self.polinizador)
        self.assertEqual(pollination.pollination_type, self.self_type)
        self.assertIsNone(pollination.father_plant)  # Self pollination has no father
        
        # Step 2: Verify automatic date calculation
        expected_maturation = pollination.pollination_date + timedelta(days=120)
        self.assertEqual(pollination.estimated_maturation_date, expected_maturation)
        
        # Step 3: Trigger alert generation (simulating signal)
        alert_service = AlertGeneratorService()
        alert_service.generate_weekly_alert(pollination)
        
        # Verify weekly alert creation
        weekly_alerts = Alert.objects.filter(
            pollination_record=pollination,
            alert_type__name='semanal'
        )
        self.assertEqual(weekly_alerts.count(), 1)
        
        weekly_alert = weekly_alerts.first()
        self.assertIn('polinización', weekly_alert.title.lower())
        self.assertEqual(weekly_alert.status, 'pending')
        
        # Verify user alert creation
        user_alerts = UserAlert.objects.filter(
            user=self.polinizador,
            alert=weekly_alert
        )
        self.assertEqual(user_alerts.count(), 1)
        
        # Step 4: Test preventive alert generation (simulate time passing)
        alert_service.generate_preventive_alert(pollination)
        
        preventive_alerts = Alert.objects.filter(
            pollination_record=pollination,
            alert_type__name='preventiva'
        )
        self.assertEqual(preventive_alerts.count(), 1)
        
        # Step 5: Test API access to alerts
        alerts_response = self.client.get('/api/alerts/user-alerts/')
        self.assertEqual(alerts_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(alerts_response.data), 2)  # At least weekly and preventive
        
        # Step 6: Test record update workflow
        update_data = {
            'is_successful': True,
            'maturation_confirmed': True,
            'observations': 'Updated: Successful pollination confirmed'
        }
        
        update_response = self.client.patch(f'/api/pollination/records/{pollination_id}/', update_data)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Verify update
        pollination.refresh_from_db()
        self.assertTrue(pollination.is_successful)
        self.assertTrue(pollination.maturation_confirmed)

    def test_complete_sibling_pollination_workflow(self):
        """Test complete sibling pollination workflow."""
        # Step 1: Create sibling pollination record
        pollination_data = {
            'responsible': self.polinizador.id,
            'pollination_type': self.sibling_type.id,
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.mother_plant.id,
            'father_plant': self.father_plant.id,  # Required for sibling
            'new_plant': self.new_plant.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 3,
            'observations': 'Test sibling pollination workflow'
        }
        
        response = self.client.post('/api/pollination/records/', pollination_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify sibling-specific validations
        pollination = PollinationRecord.objects.get(id=response.data['id'])
        self.assertIsNotNone(pollination.father_plant)
        self.assertEqual(pollination.mother_plant.species, pollination.father_plant.species)
        
        # Step 2: Test validation errors for invalid sibling pollination
        invalid_father = PlantFactory(genus='Phalaenopsis', species='amabilis')  # Different species
        invalid_data = pollination_data.copy()
        invalid_data['father_plant'] = invalid_father.id
        
        invalid_response = self.client.post('/api/pollination/records/', invalid_data)
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 3: Test alert generation for sibling pollination
        alert_service = AlertGeneratorService()
        alert_service.generate_weekly_alert(pollination)
        
        alerts = Alert.objects.filter(pollination_record=pollination)
        self.assertGreater(alerts.count(), 0)

    def test_complete_hybrid_pollination_workflow(self):
        """Test complete hybrid pollination workflow."""
        # Create plants of different species for hybrid
        hybrid_father = PlantFactory(genus='Phalaenopsis', species='amabilis')
        hybrid_new = PlantFactory(genus='Cattleya', species='hybrid')
        
        # Step 1: Create hybrid pollination record
        pollination_data = {
            'responsible': self.polinizador.id,
            'pollination_type': self.hybrid_type.id,
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.mother_plant.id,
            'father_plant': hybrid_father.id,  # Different species allowed
            'new_plant': hybrid_new.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 2,
            'observations': 'Test hybrid pollination workflow'
        }
        
        response = self.client.post('/api/pollination/records/', pollination_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify hybrid-specific characteristics
        pollination = PollinationRecord.objects.get(id=response.data['id'])
        self.assertIsNotNone(pollination.father_plant)
        self.assertNotEqual(pollination.mother_plant.species, pollination.father_plant.species)
        
        # Step 2: Test complete workflow with alerts
        alert_service = AlertGeneratorService()
        alert_service.generate_weekly_alert(pollination)
        alert_service.generate_preventive_alert(pollination)
        
        # Verify multiple alert types
        weekly_alerts = Alert.objects.filter(
            pollination_record=pollination,
            alert_type__name='semanal'
        )
        preventive_alerts = Alert.objects.filter(
            pollination_record=pollination,
            alert_type__name='preventiva'
        )
        
        self.assertEqual(weekly_alerts.count(), 1)
        self.assertEqual(preventive_alerts.count(), 1)

    def test_pollination_workflow_with_business_logic(self):
        """Test pollination workflow with business logic validation."""
        # Step 1: Test date validation (future date should fail)
        future_date = date.today() + timedelta(days=1)
        invalid_data = {
            'responsible': self.polinizador.id,
            'pollination_type': self.self_type.id,
            'pollination_date': future_date.isoformat(),
            'mother_plant': self.mother_plant.id,
            'new_plant': self.new_plant.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 5
        }
        
        response = self.client.post('/api/pollination/records/', invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('future', str(response.data).lower())
        
        # Step 2: Test duplicate prevention
        valid_data = invalid_data.copy()
        valid_data['pollination_date'] = date.today().isoformat()
        
        # Create first record
        response1 = self.client.post('/api/pollination/records/', valid_data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Try to create duplicate
        response2 = self.client.post('/api/pollination/records/', valid_data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 3: Test service layer calculations
        pollination = PollinationRecord.objects.get(id=response1.data['id'])
        service = PollinationService()
        
        # Test maturation date calculation
        calculated_date = service.calculate_maturation_date(
            pollination.pollination_date,
            pollination.pollination_type
        )
        self.assertEqual(calculated_date, pollination.estimated_maturation_date)

    def test_pollination_workflow_error_handling(self):
        """Test error handling in pollination workflow."""
        # Step 1: Test missing required fields
        incomplete_data = {
            'responsible': self.polinizador.id,
            'pollination_type': self.self_type.id,
            # Missing required fields
        }
        
        response = self.client.post('/api/pollination/records/', incomplete_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 2: Test invalid foreign key references
        invalid_data = {
            'responsible': self.polinizador.id,
            'pollination_type': 99999,  # Non-existent type
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.mother_plant.id,
            'new_plant': self.new_plant.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 5
        }
        
        response = self.client.post('/api/pollination/records/', invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 3: Test unauthorized access
        unauthorized_client = APIClient()
        response = unauthorized_client.post('/api/pollination/records/', {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pollination_workflow_with_multiple_users(self):
        """Test pollination workflow with multiple users and permissions."""
        # Create additional users
        polinizador2 = PolinizadorUserFactory()
        germinador = User.objects.create_user(
            username='germinador1',
            email='germinador1@test.com',
            password='testpass123'
        )
        germinador.role = self.polinizador.role.__class__.objects.get(name='Germinador')
        germinador.save()
        
        # Step 1: Create pollination as polinizador1
        pollination_data = {
            'responsible': self.polinizador.id,
            'pollination_type': self.self_type.id,
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.mother_plant.id,
            'new_plant': self.new_plant.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 5
        }
        
        response = self.client.post('/api/pollination/records/', pollination_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pollination_id = response.data['id']
        
        # Step 2: Test access as polinizador2
        client2 = APIClient()
        client2.force_authenticate(user=polinizador2)
        
        response2 = client2.get(f'/api/pollination/records/{pollination_id}/')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Step 3: Test access as germinador (should have limited access)
        client3 = APIClient()
        client3.force_authenticate(user=germinador)
        
        response3 = client3.get(f'/api/pollination/records/{pollination_id}/')
        # Depending on permissions, this might be 200 or 403
        self.assertIn(response3.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        
        # Step 4: Test alert visibility per user
        alert_service = AlertGeneratorService()
        alert_service.generate_weekly_alert(PollinationRecord.objects.get(id=pollination_id))
        
        # Check alerts for original user
        alerts_response = self.client.get('/api/alerts/user-alerts/')
        self.assertEqual(alerts_response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(alerts_response.data), 0)
        
        # Check alerts for other users (should be empty or different)
        alerts_response2 = client2.get('/api/alerts/user-alerts/')
        alerts_response3 = client3.get('/api/alerts/user-alerts/')
        
        # Original user should have alerts, others might not
        original_alert_count = len(alerts_response.data)
        other_alert_count = len(alerts_response2.data) if alerts_response2.status_code == 200 else 0
        
        self.assertGreaterEqual(original_alert_count, other_alert_count)