from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
from authentication.models import CustomUser, Role
from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord


class PlantViewSetTest(APITestCase):
    """Test cases for PlantViewSet."""
    
    def setUp(self):
        """Set up test data."""
        # Create role and user
        self.role = Role.objects.create(name='Polinizador')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create test plant
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
    
    def test_list_plants(self):
        """Test listing plants."""
        url = reverse('pollination:plant-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['genus'], 'Orchidaceae')
    
    def test_create_plant(self):
        """Test creating a new plant."""
        url = reverse('pollination:plant-list')
        data = {
            'genus': 'Orchidaceae',
            'species': 'dendrobium',
            'vivero': 'Vivero 2',
            'mesa': 'Mesa 1',
            'pared': 'Pared A'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Plant.objects.count(), 2)
    
    def test_create_duplicate_plant(self):
        """Test creating a duplicate plant (should fail)."""
        url = reverse('pollination:plant-list')
        data = {
            'genus': 'Orchidaceae',
            'species': 'cattleya',
            'vivero': 'Vivero 1',
            'mesa': 'Mesa 1',
            'pared': 'Pared A'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_plant_detail(self):
        """Test getting plant detail."""
        url = reverse('pollination:plant-detail', kwargs={'pk': self.plant.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['genus'], 'Orchidaceae')
        self.assertEqual(response.data['full_scientific_name'], 'Orchidaceae cattleya')
    
    def test_update_plant(self):
        """Test updating a plant."""
        url = reverse('pollination:plant-detail', kwargs={'pk': self.plant.pk})
        data = {
            'genus': 'Orchidaceae',
            'species': 'cattleya',
            'vivero': 'Vivero Updated',
            'mesa': 'Mesa 1',
            'pared': 'Pared A'
        }
        
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.vivero, 'Vivero Updated')
    
    def test_plants_by_species(self):
        """Test getting plants grouped by species."""
        url = reverse('pollination:plant-by-species')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Orchidaceae cattleya', response.data)
    
    def test_plant_locations(self):
        """Test getting unique plant locations."""
        url = reverse('pollination:plant-locations')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Vivero 1', response.data)


class PollinationTypeViewSetTest(APITestCase):
    """Test cases for PollinationTypeViewSet."""
    
    def setUp(self):
        """Set up test data."""
        # Create role and user
        self.role = Role.objects.create(name='Polinizador')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create test pollination type
        self.pollination_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización'
        )
        
        # Create test plants
        self.mother_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        self.father_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='dendrobium',
            vivero='Vivero 1',
            mesa='Mesa 2',
            pared='Pared B'
        )
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
    
    def test_list_pollination_types(self):
        """Test listing pollination types."""
        url = reverse('pollination:pollinationtype-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Self')
    
    def test_get_pollination_type_detail(self):
        """Test getting pollination type detail."""
        url = reverse('pollination:pollinationtype-detail', kwargs={'pk': self.pollination_type.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Self')
        self.assertFalse(response.data['requires_father_plant'])
    
    def test_validate_compatibility_self_valid(self):
        """Test plant compatibility validation for Self pollination."""
        url = reverse('pollination:pollinationtype-validate-compatibility', 
                     kwargs={'pk': self.pollination_type.pk})
        data = {
            'mother_plant_id': self.mother_plant.id
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_compatible'])
    
    def test_validate_compatibility_self_with_father(self):
        """Test plant compatibility validation for Self with father plant."""
        url = reverse('pollination:pollinationtype-validate-compatibility', 
                     kwargs={'pk': self.pollination_type.pk})
        data = {
            'mother_plant_id': self.mother_plant.id,
            'father_plant_id': self.father_plant.id
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_compatible'])


class ClimateConditionViewSetTest(APITestCase):
    """Test cases for ClimateConditionViewSet."""
    
    def setUp(self):
        """Set up test data."""
        # Create role and user
        self.role = Role.objects.create(name='Polinizador')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create test climate condition
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=65
        )
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
    
    def test_list_climate_conditions(self):
        """Test listing climate conditions."""
        url = reverse('pollination:climatecondition-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['weather'], 'Soleado')
    
    def test_create_climate_condition(self):
        """Test creating a new climate condition."""
        url = reverse('pollination:climatecondition-list')
        data = {
            'weather': 'Nublado',
            'temperature': 20.0,
            'humidity': 80,
            'wind_speed': 5.0
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ClimateCondition.objects.count(), 2)
    
    def test_create_climate_condition_invalid_humidity(self):
        """Test creating climate condition with invalid humidity."""
        url = reverse('pollination:climatecondition-list')
        data = {
            'weather': 'Soleado',
            'humidity': 150  # Invalid humidity
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_recent_climate_conditions(self):
        """Test getting recent climate conditions."""
        url = reverse('pollination:climatecondition-recent')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class PollinationRecordViewSetTest(APITestCase):
    """Test cases for PollinationRecordViewSet."""
    
    def setUp(self):
        """Set up test data."""
        # Create role and user
        self.role = Role.objects.create(name='Polinizador')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create test plants
        self.mother_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        self.new_plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 2',
            pared='Pared B'
        )
        
        # Create pollination type
        self.pollination_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización'
        )
        
        # Create climate condition
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=65
        )
        
        # Create test record
        self.record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today(),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
    
    def test_list_pollination_records(self):
        """Test listing pollination records."""
        url = reverse('pollination:pollinationrecord-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['capsules_quantity'], 5)
    
    def test_create_pollination_record(self):
        """Test creating a new pollination record."""
        url = reverse('pollination:pollinationrecord-list')
        data = {
            'pollination_type': self.pollination_type.id,
            'pollination_date': date.today().isoformat(),
            'mother_plant': self.mother_plant.id,
            'new_plant': self.new_plant.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 3,
            'observations': 'Test record'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PollinationRecord.objects.count(), 2)
    
    def test_create_pollination_record_future_date(self):
        """Test creating pollination record with future date (should fail)."""
        url = reverse('pollination:pollinationrecord-list')
        future_date = date.today() + timedelta(days=1)
        data = {
            'pollination_type': self.pollination_type.id,
            'pollination_date': future_date.isoformat(),
            'mother_plant': self.mother_plant.id,
            'new_plant': self.new_plant.id,
            'climate_condition': self.climate.id,
            'capsules_quantity': 3
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_pollination_record_detail(self):
        """Test getting pollination record detail."""
        url = reverse('pollination:pollinationrecord-detail', kwargs={'pk': self.record.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['capsules_quantity'], 5)
        self.assertIsNotNone(response.data['estimated_maturation_date'])
        self.assertIsNotNone(response.data['days_to_maturation'])
    
    def test_confirm_maturation(self):
        """Test confirming maturation of a record."""
        # Create an older record that can be confirmed
        old_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=100),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=3
        )
        
        url = reverse('pollination:pollinationrecord-confirm-maturation', 
                     kwargs={'pk': old_record.pk})
        data = {
            'is_successful': True,
            'notes': 'Maturation confirmed successfully'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        old_record.refresh_from_db()
        self.assertTrue(old_record.maturation_confirmed)
        self.assertTrue(old_record.is_successful)
    
    def test_get_statistics(self):
        """Test getting pollination statistics."""
        url = reverse('pollination:pollinationrecord-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_records', response.data)
        self.assertIn('success_rate', response.data)
        self.assertEqual(response.data['total_records'], 1)
    
    def test_get_pending_maturation(self):
        """Test getting records pending maturation."""
        url = reverse('pollination:pollinationrecord-pending-maturation')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be empty since our test record is not approaching maturation
        self.assertEqual(len(response.data), 0)
    
    def test_get_overdue_records(self):
        """Test getting overdue records."""
        # Create an overdue record
        overdue_record = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date.today() - timedelta(days=130),
            mother_plant=self.mother_plant,
            new_plant=self.new_plant,
            climate_condition=self.climate,
            capsules_quantity=2
        )
        
        url = reverse('pollination:pollinationrecord-overdue')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], overdue_record.id)
    
    def test_get_records_by_type(self):
        """Test getting records grouped by type."""
        url = reverse('pollination:pollinationrecord-by-type')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Self', response.data)
        self.assertEqual(len(response.data['Self']), 1)
    
    def test_get_dashboard_summary(self):
        """Test getting dashboard summary."""
        url = reverse('pollination:pollinationrecord-dashboard-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('counts', response.data)
        self.assertIn('recent_records', response.data)
        self.assertIn('alerts', response.data)
    
    def test_filter_by_maturation_status(self):
        """Test filtering records by maturation status."""
        url = reverse('pollination:pollinationrecord-list')
        response = self.client.get(url, {'maturation_status': 'pending'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_search_records(self):
        """Test searching records."""
        url = reverse('pollination:pollinationrecord-list')
        response = self.client.get(url, {'search': 'Orchidaceae'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class PermissionTest(APITestCase):
    """Test cases for API permissions."""
    
    def setUp(self):
        """Set up test data."""
        # Create different roles
        self.polinizador_role = Role.objects.create(name='Polinizador')
        self.admin_role = Role.objects.create(name='Administrador')
        
        # Create users with different roles
        self.polinizador = CustomUser.objects.create_user(
            username='polinizador',
            email='polinizador@example.com',
            password='testpass123',
            role=self.polinizador_role
        )
        
        self.admin = CustomUser.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        # Create test plant
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access APIs."""
        url = reverse('pollination:plant-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_polinizador_can_access_plants(self):
        """Test that polinizador can access plant APIs."""
        self.client.force_authenticate(user=self.polinizador)
        url = reverse('pollination:plant-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_admin_can_access_all_records(self):
        """Test that admin can access all records."""
        # Create record by polinizador
        pollination_type = PollinationType.objects.create(name='Self', description='Test')
        climate = ClimateCondition.objects.create(weather='Soleado')
        
        record = PollinationRecord.objects.create(
            responsible=self.polinizador,
            pollination_type=pollination_type,
            pollination_date=date.today(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=climate,
            capsules_quantity=5
        )
        
        # Admin should see all records
        self.client.force_authenticate(user=self.admin)
        url = reverse('pollination:pollinationrecord-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_polinizador_sees_only_own_records(self):
        """Test that polinizador sees only their own records."""
        # Create record by admin
        pollination_type = PollinationType.objects.create(name='Self', description='Test')
        climate = ClimateCondition.objects.create(weather='Soleado')
        
        record = PollinationRecord.objects.create(
            responsible=self.admin,
            pollination_type=pollination_type,
            pollination_date=date.today(),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=climate,
            capsules_quantity=5
        )
        
        # Polinizador should not see admin's records
        self.client.force_authenticate(user=self.polinizador)
        url = reverse('pollination:pollinationrecord-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)