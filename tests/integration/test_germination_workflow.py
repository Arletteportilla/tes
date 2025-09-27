"""
Integration tests for complete germination workflow.
Tests the end-to-end process from germination record creation to alert generation.
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from factories import (
    GerminadorUserFactory, PlantFactory, SeedSourceFactory, 
    GerminationConditionFactory, GerminationRecordFactory,
    PollinationRecordFactory
)
from germination.models import GerminationRecord, SeedSource
from alerts.models import Alert, UserAlert
from alerts.services import AlertGeneratorService
from germination.services import GerminationService

User = get_user_model()


@pytest.mark.django_db
class TestGerminationWorkflowIntegration(TransactionTestCase):
    """Test complete germination workflow integration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.germinador = GerminadorUserFactory()
        self.client.force_authenticate(user=self.germinador)
        
        # Create required data
        self.plant = PlantFactory(genus='Cattleya', species='trianae')
        self.seed_source = SeedSourceFactory(source_type='Autopolinización')
        self.germination_condition = GerminationConditionFactory()

    def test_complete_germination_workflow_from_internal_source(self):
        """Test complete germination workflow using internal seed source."""
        # Step 1: Create pollination record first (for seed source)
        pollination = PollinationRecordFactory()
        internal_seed_source = SeedSourceFactory(
            source_type='Autopolinización',
            pollination_record=pollination
        )
        
        # Step 2: Create germination record via API
        germination_data = {
            'responsible': self.germinador.id,
            'germination_date': date.today().isoformat(),
            'plant': self.plant.id,
            'seed_source': internal_seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 50,
            'transplant_days': 90,
            'observations': 'Test germination workflow from internal source'
        }
        
        response = self.client.post('/api/germination/records/', germination_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify record creation
        germination_id = response.data['id']
        germination = GerminationRecord.objects.get(id=germination_id)
        self.assertEqual(germination.responsible, self.germinador)
        self.assertEqual(germination.seed_source, internal_seed_source)
        self.assertEqual(germination.seed_source.pollination_record, pollination)
        
        # Step 3: Verify automatic date calculation
        expected_transplant = germination.germination_date + timedelta(days=90)
        self.assertEqual(germination.estimated_transplant_date, expected_transplant)
        
        # Step 4: Trigger alert generation
        alert_service = AlertGeneratorService()
        alert_service.generate_weekly_alert_germination(germination)
        
        # Verify weekly alert creation
        weekly_alerts = Alert.objects.filter(
            germination_record=germination,
            alert_type__name='semanal'
        )
        self.assertEqual(weekly_alerts.count(), 1)
        
        weekly_alert = weekly_alerts.first()
        self.assertIn('germinación', weekly_alert.title.lower())
        self.assertEqual(weekly_alert.status, 'pending')
        
        # Step 5: Test preventive alert generation
        alert_service.generate_preventive_alert_germination(germination)
        
        preventive_alerts = Alert.objects.filter(
            germination_record=germination,
            alert_type__name='preventiva'
        )
        self.assertEqual(preventive_alerts.count(), 1)
        
        # Step 6: Test API access to alerts
        alerts_response = self.client.get('/api/alerts/user-alerts/')
        self.assertEqual(alerts_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(alerts_response.data), 2)
        
        # Step 7: Test record update with germination results
        update_data = {
            'seedlings_germinated': 35,  # 70% success rate
            'is_successful': True,
            'transplant_confirmed': True,
            'transplant_confirmed_date': date.today().isoformat(),
            'observations': 'Updated: 35 seedlings successfully germinated and transplanted'
        }
        
        update_response = self.client.patch(f'/api/germination/records/{germination_id}/', update_data)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Verify update
        germination.refresh_from_db()
        self.assertEqual(germination.seedlings_germinated, 35)
        self.assertTrue(germination.is_successful)
        self.assertTrue(germination.transplant_confirmed)

    def test_complete_germination_workflow_from_external_source(self):
        """Test complete germination workflow using external seed source."""
        # Step 1: Create external seed source
        external_seed_source = SeedSourceFactory(
            source_type='Otra fuente',
            external_supplier='Vivero Especializado S.A.',
            pollination_record=None
        )
        
        # Step 2: Create germination record
        germination_data = {
            'responsible': self.germinador.id,
            'germination_date': date.today().isoformat(),
            'plant': self.plant.id,
            'seed_source': external_seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 25,
            'transplant_days': 90,
            'observations': 'Test germination workflow from external source'
        }
        
        response = self.client.post('/api/germination/records/', germination_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify external source characteristics
        germination = GerminationRecord.objects.get(id=response.data['id'])
        self.assertEqual(germination.seed_source.source_type, 'Otra fuente')
        self.assertIsNone(germination.seed_source.pollination_record)
        self.assertEqual(germination.seed_source.external_supplier, 'Vivero Especializado S.A.')

    def test_germination_workflow_with_different_conditions(self):
        """Test germination workflow with different environmental conditions."""
        # Test different climate conditions
        conditions = [
            GerminationConditionFactory(climate='Controlado', substrate='Turba'),
            GerminationConditionFactory(climate='Invernadero', substrate='Perlita'),
            GerminationConditionFactory(climate='Laboratorio', substrate='Musgo sphagnum')
        ]
        
        for i, condition in enumerate(conditions):
            germination_data = {
                'responsible': self.germinador.id,
                'germination_date': date.today().isoformat(),
                'plant': PlantFactory().id,
                'seed_source': SeedSourceFactory().id,
                'germination_condition': condition.id,
                'seeds_planted': 20 + i * 10,
                'transplant_days': 90,
                'observations': f'Test with {condition.climate} climate and {condition.substrate} substrate'
            }
            
            response = self.client.post('/api/germination/records/', germination_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            # Verify condition-specific data
            germination = GerminationRecord.objects.get(id=response.data['id'])
            self.assertEqual(germination.germination_condition.climate, condition.climate)
            self.assertEqual(germination.germination_condition.substrate, condition.substrate)

    def test_germination_workflow_business_logic_validation(self):
        """Test germination workflow with business logic validation."""
        # Step 1: Test date validation (future date should fail)
        future_date = date.today() + timedelta(days=1)
        invalid_data = {
            'responsible': self.germinador.id,
            'germination_date': future_date.isoformat(),
            'plant': self.plant.id,
            'seed_source': self.seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 30
        }
        
        response = self.client.post('/api/germination/records/', invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('future', str(response.data).lower())
        
        # Step 2: Test seedlings_germinated validation (cannot exceed seeds_planted)
        valid_data = invalid_data.copy()
        valid_data['germination_date'] = date.today().isoformat()
        
        response = self.client.post('/api/germination/records/', valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Try to update with invalid seedlings count
        invalid_update = {
            'seedlings_germinated': 50  # More than seeds_planted (30)
        }
        
        update_response = self.client.patch(f'/api/germination/records/{response.data["id"]}/', invalid_update)
        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 3: Test service layer calculations
        germination = GerminationRecord.objects.get(id=response.data['id'])
        service = GerminationService()
        
        calculated_date = service.calculate_transplant_date(
            germination.germination_date,
            germination.transplant_days
        )
        self.assertEqual(calculated_date, germination.estimated_transplant_date)

    def test_germination_workflow_with_success_tracking(self):
        """Test germination workflow with success rate tracking."""
        # Step 1: Create multiple germination records with different success rates
        test_cases = [
            {'seeds_planted': 100, 'seedlings_germinated': 85, 'expected_success': True},
            {'seeds_planted': 50, 'seedlings_germinated': 45, 'expected_success': True},
            {'seeds_planted': 30, 'seedlings_germinated': 10, 'expected_success': False},
            {'seeds_planted': 20, 'seedlings_germinated': 0, 'expected_success': False}
        ]
        
        germination_ids = []
        
        for i, case in enumerate(test_cases):
            germination_data = {
                'responsible': self.germinador.id,
                'germination_date': (date.today() - timedelta(days=i)).isoformat(),
                'plant': PlantFactory().id,
                'seed_source': SeedSourceFactory().id,
                'germination_condition': self.germination_condition.id,
                'seeds_planted': case['seeds_planted'],
                'transplant_days': 90,
                'observations': f'Test case {i+1}'
            }
            
            response = self.client.post('/api/germination/records/', germination_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            germination_ids.append(response.data['id'])
            
            # Update with germination results
            update_data = {
                'seedlings_germinated': case['seedlings_germinated'],
                'is_successful': case['expected_success']
            }
            
            update_response = self.client.patch(f'/api/germination/records/{response.data["id"]}/', update_data)
            self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Step 2: Verify success rate calculations
        for i, germination_id in enumerate(germination_ids):
            germination = GerminationRecord.objects.get(id=germination_id)
            expected_rate = test_cases[i]['seedlings_germinated'] / test_cases[i]['seeds_planted']
            actual_rate = germination.success_rate
            
            self.assertAlmostEqual(actual_rate, expected_rate, places=2)
            self.assertEqual(germination.is_successful, test_cases[i]['expected_success'])

    def test_germination_workflow_alert_generation_timing(self):
        """Test alert generation timing for germination workflow."""
        # Step 1: Create germination record
        germination_data = {
            'responsible': self.germinador.id,
            'germination_date': date.today().isoformat(),
            'plant': self.plant.id,
            'seed_source': self.seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 40,
            'transplant_days': 90
        }
        
        response = self.client.post('/api/germination/records/', germination_data)
        germination = GerminationRecord.objects.get(id=response.data['id'])
        
        # Step 2: Test weekly alert timing (should be scheduled for 1 week after germination)
        alert_service = AlertGeneratorService()
        alert_service.generate_weekly_alert_germination(germination)
        
        weekly_alert = Alert.objects.filter(
            germination_record=germination,
            alert_type__name='semanal'
        ).first()
        
        expected_weekly_date = germination.germination_date + timedelta(days=7)
        self.assertEqual(weekly_alert.scheduled_date.date(), expected_weekly_date)
        
        # Step 3: Test preventive alert timing (should be scheduled for 1 week before transplant)
        alert_service.generate_preventive_alert_germination(germination)
        
        preventive_alert = Alert.objects.filter(
            germination_record=germination,
            alert_type__name='preventiva'
        ).first()
        
        expected_preventive_date = germination.estimated_transplant_date - timedelta(days=7)
        self.assertEqual(preventive_alert.scheduled_date.date(), expected_preventive_date)

    def test_germination_workflow_error_handling(self):
        """Test error handling in germination workflow."""
        # Step 1: Test missing required fields
        incomplete_data = {
            'responsible': self.germinador.id,
            'germination_date': date.today().isoformat(),
            # Missing required fields
        }
        
        response = self.client.post('/api/germination/records/', incomplete_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 2: Test invalid foreign key references
        invalid_data = {
            'responsible': self.germinador.id,
            'germination_date': date.today().isoformat(),
            'plant': 99999,  # Non-existent plant
            'seed_source': self.seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 30
        }
        
        response = self.client.post('/api/germination/records/', invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 3: Test unauthorized access
        unauthorized_client = APIClient()
        response = unauthorized_client.post('/api/germination/records/', {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_germination_workflow_cross_module_integration(self):
        """Test germination workflow integration with pollination module."""
        # Step 1: Create complete pollination -> germination chain
        pollination = PollinationRecordFactory(responsible=self.germinador)
        
        # Step 2: Create seed source from pollination
        seed_source = SeedSourceFactory(
            source_type='Autopolinización',
            pollination_record=pollination
        )
        
        # Step 3: Create germination record using seeds from pollination
        germination_data = {
            'responsible': self.germinador.id,
            'germination_date': date.today().isoformat(),
            'plant': pollination.new_plant.id,  # Use the new plant from pollination
            'seed_source': seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 30,
            'transplant_days': 90,
            'observations': 'Germination from internal pollination record'
        }
        
        response = self.client.post('/api/germination/records/', germination_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 4: Verify cross-module relationships
        germination = GerminationRecord.objects.get(id=response.data['id'])
        self.assertEqual(germination.seed_source.pollination_record, pollination)
        self.assertEqual(germination.plant, pollination.new_plant)
        
        # Step 5: Test alert generation for both modules
        alert_service = AlertGeneratorService()
        
        # Generate alerts for pollination
        alert_service.generate_weekly_alert(pollination)
        
        # Generate alerts for germination
        alert_service.generate_weekly_alert_germination(germination)
        
        # Verify both types of alerts exist
        pollination_alerts = Alert.objects.filter(pollination_record=pollination)
        germination_alerts = Alert.objects.filter(germination_record=germination)
        
        self.assertGreater(pollination_alerts.count(), 0)
        self.assertGreater(germination_alerts.count(), 0)
        
        # Step 6: Test user alert aggregation
        user_alerts = UserAlert.objects.filter(user=self.germinador)
        self.assertGreaterEqual(user_alerts.count(), 2)  # At least one from each module