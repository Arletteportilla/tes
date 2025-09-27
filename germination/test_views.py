"""
Integration tests for germination views and APIs.
Tests complete API functionality including authentication and permissions.
"""

from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import GerminationRecord, SeedSource, GerminationCondition
from pollination.models import Plant, PollinationType, PollinationRecord, ClimateCondition
from authentication.models import Role

User = get_user_model()


class GerminationAPITestCase(TestCase):
    """Base test case for germination API tests."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create roles
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Administrator role',
            permissions={'all': True}
        )
        self.germinador_role = Role.objects.create(
            name='Germinador',
            description='Germination specialist role',
            permissions={'germination': True}
        )
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        self.germinador_user = User.objects.create_user(
            username='germinador',
            email='germinador@example.com',
            password='testpass123',
            role=self.germinador_role
        )
        
        # Create test data
        self.plant = Plant.objects.create(
            genus='Test',
            species='species',
            vivero='Test Vivero',
            mesa='Test Mesa',
            pared='Test Pared'
        )
        
        self.seed_source = SeedSource.objects.create(
            name='Test Source',
            source_type='Otra fuente',
            external_supplier='Test Supplier'
        )
        
        self.germination_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Test Location'
        )
    
    def get_jwt_token(self, user):
        """Get JWT token for user."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """Authenticate user for API requests."""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class GerminationRecordViewSetTest(GerminationAPITestCase):
    """Test cases for GerminationRecordViewSet."""
    
    def test_create_germination_record_authenticated(self):
        """Test creating germination record with authenticated user."""
        self.authenticate_user(self.germinador_user)
        
        data = {
            'germination_date': str(date.today() - timedelta(days=1)),
            'plant': self.plant.id,
            'seed_source': self.seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 10,
            'seedlings_germinated': 8,
            'transplant_days': 90,
            'observations': 'Test observation'
        }
        
        url = reverse('germination:germinationrecord-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GerminationRecord.objects.count(), 1)
        
        record = GerminationRecord.objects.first()
        self.assertEqual(record.responsible, self.germinador_user)
        self.assertEqual(record.seeds_planted, 10)
        self.assertEqual(record.seedlings_germinated, 8)
    
    def test_create_germination_record_unauthenticated(self):
        """Test creating germination record without authentication."""
        data = {
            'germination_date': str(date.today() - timedelta(days=1)),
            'plant': self.plant.id,
            'seed_source': self.seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 10
        }
        
        url = reverse('germination:germinationrecord-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(GerminationRecord.objects.count(), 0)
    
    def test_list_germination_records(self):
        """Test listing germination records."""
        self.authenticate_user(self.germinador_user)
        
        # Create test records
        GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=5),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10,
            seedlings_germinated=8
        )
        
        url = reverse('germination:germinationrecord-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_germination_record(self):
        """Test retrieving specific germination record."""
        self.authenticate_user(self.germinador_user)
        
        record = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=5),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10,
            seedlings_germinated=8
        )
        
        url = reverse('germination:germinationrecord-detail', kwargs={'pk': record.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], record.id)
        self.assertEqual(response.data['seeds_planted'], 10)
        self.assertIn('plant_details', response.data)
        self.assertIn('transplant_recommendations', response.data)
    
    def test_update_germination_record(self):
        """Test updating germination record."""
        self.authenticate_user(self.germinador_user)
        
        record = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=5),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10,
            seedlings_germinated=8
        )
        
        data = {
            'seedlings_germinated': 9,
            'observations': 'Updated observation'
        }
        
        url = reverse('germination:germinationrecord-detail', kwargs={'pk': record.id})
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        record.refresh_from_db()
        self.assertEqual(record.seedlings_germinated, 9)
        self.assertEqual(record.observations, 'Updated observation')
    
    def test_delete_germination_record_non_admin(self):
        """Test that non-admin users cannot delete records."""
        self.authenticate_user(self.germinador_user)
        
        record = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=5),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
        
        url = reverse('germination:germinationrecord-detail', kwargs={'pk': record.id})
        response = self.client.delete(url)
        
        # Should be forbidden for non-admin users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(GerminationRecord.objects.filter(id=record.id).exists())
    
    def test_statistics_endpoint(self):
        """Test statistics endpoint."""
        self.authenticate_user(self.germinador_user)
        
        # Create test records
        for i in range(3):
            GerminationRecord.objects.create(
                responsible=self.germinador_user,
                germination_date=date.today() - timedelta(days=i+1),
                plant=self.plant,
                seed_source=self.seed_source,
                germination_condition=self.germination_condition,
                seeds_planted=10,
                seedlings_germinated=8 if i < 2 else 6,
                is_successful=True if i < 2 else False
            )
        
        url = reverse('germination:germinationrecord-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_records'], 3)
        self.assertEqual(response.data['total_seeds_planted'], 30)
        self.assertEqual(response.data['total_seedlings_germinated'], 22)
    
    def test_pending_transplants_endpoint(self):
        """Test pending transplants endpoint."""
        self.authenticate_user(self.germinador_user)
        
        # Create record with upcoming transplant
        record = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=60),
            estimated_transplant_date=date.today() + timedelta(days=15),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
        
        url = reverse('germination:germinationrecord-pending-transplants')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['germination_record_id'], record.id)
    
    def test_overdue_transplants_endpoint(self):
        """Test overdue transplants endpoint."""
        self.authenticate_user(self.germinador_user)
        
        # Create record with overdue transplant
        record = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=120),
            estimated_transplant_date=date.today() - timedelta(days=10),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
        
        url = reverse('germination:germinationrecord-overdue-transplants')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['germination_record_id'], record.id)
        self.assertEqual(response.data[0]['status'], 'overdue')
    
    def test_confirm_transplant_endpoint(self):
        """Test confirm transplant endpoint."""
        self.authenticate_user(self.germinador_user)
        
        record = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=90),
            estimated_transplant_date=date.today() - timedelta(days=5),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
        
        data = {
            'confirmed_date': date.today(),
            'is_successful': True
        }
        
        url = reverse('germination:germinationrecord-confirm-transplant', kwargs={'pk': record.id})
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        record.refresh_from_db()
        self.assertTrue(record.transplant_confirmed)
        self.assertTrue(record.is_successful)
    
    def test_validation_errors(self):
        """Test validation errors in record creation."""
        self.authenticate_user(self.germinador_user)
        
        # Test future date
        data = {
            'germination_date': str(date.today() + timedelta(days=1)),
            'plant': self.plant.id,
            'seed_source': self.seed_source.id,
            'germination_condition': self.germination_condition.id,
            'seeds_planted': 10
        }
        
        url = reverse('germination:germinationrecord-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)


class SeedSourceViewSetTest(GerminationAPITestCase):
    """Test cases for SeedSourceViewSet."""
    
    def test_create_seed_source(self):
        """Test creating seed source."""
        self.authenticate_user(self.germinador_user)
        
        data = {
            'name': 'New Test Source',
            'source_type': 'Otra fuente',
            'external_supplier': 'New Supplier',
            'description': 'Test description'
        }
        
        url = reverse('germination:seedsource-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SeedSource.objects.count(), 2)  # One from setUp + one created
    
    def test_list_seed_sources(self):
        """Test listing seed sources."""
        self.authenticate_user(self.germinador_user)
        
        url = reverse('germination:seedsource-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_deactivate_seed_source(self):
        """Test deactivating seed source."""
        self.authenticate_user(self.admin_user)
        
        url = reverse('germination:seedsource-deactivate', kwargs={'pk': self.seed_source.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.seed_source.refresh_from_db()
        self.assertFalse(self.seed_source.is_active)
    
    def test_by_type_endpoint(self):
        """Test by type grouping endpoint."""
        self.authenticate_user(self.germinador_user)
        
        # Create another source with different type
        SeedSource.objects.create(
            name='Hybrid Source',
            source_type='Híbrido',
            external_supplier='Hybrid Supplier'
        )
        
        url = reverse('germination:seedsource-by-type')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class GerminationConditionViewSetTest(GerminationAPITestCase):
    """Test cases for GerminationConditionViewSet."""
    
    def test_create_germination_condition(self):
        """Test creating germination condition."""
        self.authenticate_user(self.germinador_user)
        
        data = {
            'climate': 'Invernadero',
            'substrate': 'Perlita',
            'location': 'New Location',
            'temperature': 25.5,
            'humidity': 80,
            'light_hours': 12
        }
        
        url = reverse('germination:germinationcondition-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GerminationCondition.objects.count(), 2)
    
    def test_list_germination_conditions(self):
        """Test listing germination conditions."""
        self.authenticate_user(self.germinador_user)
        
        url = reverse('germination:germinationcondition-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_by_climate_endpoint(self):
        """Test by climate grouping endpoint."""
        self.authenticate_user(self.germinador_user)
        
        # Create another condition with different climate
        GerminationCondition.objects.create(
            climate='Exterior',
            substrate='Turba',
            location='Outdoor Location'
        )
        
        url = reverse('germination:germinationcondition-by-climate')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_validation_errors(self):
        """Test validation errors in condition creation."""
        self.authenticate_user(self.germinador_user)
        
        # Test invalid humidity
        data = {
            'climate': 'Controlado',
            'substrate': 'Turba',
            'location': 'Test Location',
            'humidity': 150  # Invalid
        }
        
        url = reverse('germination:germinationcondition-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)


class GerminationAPIPermissionsTest(GerminationAPITestCase):
    """Test cases for API permissions and access control."""
    
    def test_user_can_only_see_own_records(self):
        """Test that non-admin users can only see their own records."""
        # Create another user
        other_user = User.objects.create_user(
            username='other_germinador',
            email='other@example.com',
            password='testpass123',
            role=self.germinador_role
        )
        
        # Create records for both users
        GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=1),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
        
        GerminationRecord.objects.create(
            responsible=other_user,
            germination_date=date.today() - timedelta(days=2),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=15
        )
        
        # Authenticate as first user
        self.authenticate_user(self.germinador_user)
        
        url = reverse('germination:germinationrecord-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Should only see own record
        self.assertEqual(response.data['results'][0]['seeds_planted'], 10)
    
    def test_admin_can_see_all_records(self):
        """Test that admin users can see all records."""
        # Create records for different users
        GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=1),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10
        )
        
        # Authenticate as admin
        self.authenticate_user(self.admin_user)
        
        url = reverse('germination:germinationrecord-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Admin can see all records
    
    def test_filtering_and_search(self):
        """Test filtering and search functionality."""
        self.authenticate_user(self.germinador_user)
        
        # Create test records with different attributes
        record1 = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=1),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=10,
            observations='First test record'
        )
        
        # Create another plant for variety
        plant2 = Plant.objects.create(
            genus='Different',
            species='species',
            vivero='Test Vivero',
            mesa='Test Mesa',
            pared='Test Pared'
        )
        
        record2 = GerminationRecord.objects.create(
            responsible=self.germinador_user,
            germination_date=date.today() - timedelta(days=2),
            plant=plant2,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=15,
            observations='Second test record'
        )
        
        # Test filtering by plant genus
        url = reverse('germination:germinationrecord-list')
        response = self.client.get(url, {'plant__genus': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Test search functionality
        response = self.client.get(url, {'search': 'First'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], record1.id)