"""
Tests for statistics services and views.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
from unittest.mock import patch

from authentication.models import CustomUser, Role
from pollination.models import Plant, PollinationType, ClimateCondition, PollinationRecord
from germination.models import SeedSource, GerminationSetup, GerminationRecord
from core.models import ClimateCondition
from .statistics_services import StatisticsService, PollinationStatisticsService, GerminationStatisticsService


class StatisticsServiceTest(TestCase):
    """Test cases for StatisticsService."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Administrador del sistema',
            permissions={'can_generate_reports': True}
        )
        
        self.user_role = Role.objects.create(
            name='Polinizador',
            description='Usuario polinizador',
            permissions={'can_create_pollination': True}
        )
        
        self.admin_user = CustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        self.admin_user.role = self.admin_role
        self.admin_user.save()
        
        self.regular_user = CustomUser.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123',
            first_name='Regular',
            last_name='User'
        )
        self.regular_user.role = self.user_role
        self.regular_user.save()
        
        # Create test plants
        self.plant1 = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero A',
            mesa='Mesa 1',
            pared='Pared 1'
        )
        
        self.plant2 = Plant.objects.create(
            genus='Orchidaceae',
            species='dendrobium',
            vivero='Vivero A',
            mesa='Mesa 2',
            pared='Pared 1'
        )
        
        self.plant3 = Plant.objects.create(
            genus='Bromeliaceae',
            species='tillandsia',
            vivero='Vivero B',
            mesa='Mesa 1',
            pared='Pared 2'
        )
        
        # Create pollination types
        self.self_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización',
            requires_father_plant=False,
            allows_different_species=False,
            maturation_days=120
        )
        
        self.hybrid_type = PollinationType.objects.create(
            name='Híbrido',
            description='Hibridación',
            requires_father_plant=True,
            allows_different_species=True,
            maturation_days=150
        )
        
        # Create climate condition
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=70
        )
        
        # Create seed sources
        self.seed_source1 = SeedSource.objects.create(
            name='Fuente 1',
            source_type='Autopolinización',
            description='Semillas de autopolinización'
        )
        
        self.seed_source2 = SeedSource.objects.create(
            name='Fuente 2',
            source_type='Híbrido',
            description='Semillas de hibridación'
        )
        
        # Create germination condition
        self.germ_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Laboratorio A',
            temperature=22.0,
            humidity=80
        )
        
        # Create test records
        self.create_test_records()
        
        # Initialize service
        self.statistics_service = StatisticsService()
    
    def create_test_records(self):
        """Create test pollination and germination records."""
        today = date.today()
        
        # Create pollination records
        self.poll_record1 = PollinationRecord.objects.create(
            responsible=self.admin_user,
            pollination_type=self.self_type,
            pollination_date=today - timedelta(days=30),
            mother_plant=self.plant1,
            new_plant=self.plant1,
            climate_condition=self.climate,
            capsules_quantity=5,
            observations='Test record 1'
        )
        
        self.poll_record2 = PollinationRecord.objects.create(
            responsible=self.regular_user,
            pollination_type=self.hybrid_type,
            pollination_date=today - timedelta(days=15),
            mother_plant=self.plant1,
            father_plant=self.plant2,
            new_plant=self.plant3,
            climate_condition=self.climate,
            capsules_quantity=3,
            observations='Test record 2'
        )
        
        self.poll_record3 = PollinationRecord.objects.create(
            responsible=self.admin_user,
            pollination_type=self.self_type,
            pollination_date=today - timedelta(days=5),
            mother_plant=self.plant2,
            new_plant=self.plant2,
            climate_condition=self.climate,
            capsules_quantity=7,
            observations='Test record 3'
        )
        
        # Create germination records
        self.germ_record1 = GerminationRecord.objects.create(
            responsible=self.admin_user,
            germination_date=today - timedelta(days=25),
            plant=self.plant1,
            seed_source=self.seed_source1,
            germination_setup=self.germ_setup,
            seeds_planted=100,
            seedlings_germinated=85,
            observations='Test germination 1'
        )
        
        self.germ_record2 = GerminationRecord.objects.create(
            responsible=self.regular_user,
            germination_date=today - timedelta(days=10),
            plant=self.plant2,
            seed_source=self.seed_source2,
            germination_setup=self.germ_setup,
            seeds_planted=50,
            seedlings_germinated=40,
            observations='Test germination 2'
        )
        
        self.germ_record3 = GerminationRecord.objects.create(
            responsible=self.admin_user,
            germination_date=today - timedelta(days=2),
            plant=self.plant3,
            seed_source=self.seed_source1,
            germination_setup=self.germ_setup,
            seeds_planted=75,
            seedlings_germinated=60,
            observations='Test germination 3'
        )
    
    def test_comprehensive_statistics_generation(self):
        """Test comprehensive statistics generation."""
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.statistics_service.get_comprehensive_statistics(parameters)
        
        # Check main structure
        self.assertIn('summary', stats)
        self.assertIn('pollination', stats)
        self.assertIn('germination', stats)
        self.assertIn('comparative', stats)
        self.assertIn('trends', stats)
        self.assertIn('performance', stats)
        self.assertIn('metadata', stats)
        
        # Check summary data
        summary = stats['summary']
        self.assertEqual(summary['total_activities'], 6)  # 3 pollination + 3 germination
        self.assertEqual(summary['pollination_records'], 3)
        self.assertEqual(summary['germination_records'], 3)
        self.assertEqual(summary['total_capsules_produced'], 15)  # 5 + 3 + 7
        self.assertEqual(summary['total_seedlings_produced'], 185)  # 85 + 40 + 60
        
        # Check activity distribution
        self.assertEqual(summary['activity_distribution']['pollination_percentage'], 50.0)
        self.assertEqual(summary['activity_distribution']['germination_percentage'], 50.0)
    
    def test_pollination_statistics(self):
        """Test pollination-specific statistics."""
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        poll_stats = self.statistics_service.pollination_stats.get_statistics(parameters)
        
        # Check structure
        self.assertIn('summary', poll_stats)
        self.assertIn('by_type', poll_stats)
        self.assertIn('by_responsible', poll_stats)
        self.assertIn('by_genus', poll_stats)
        self.assertIn('success_analysis', poll_stats)
        
        # Check summary
        summary = poll_stats['summary']
        self.assertEqual(summary['total_records'], 3)
        self.assertEqual(summary['total_capsules'], 15)
        self.assertEqual(summary['avg_capsules_per_record'], 5.0)
        self.assertEqual(summary['success_rate'], 100.0)  # All records have capsules > 0
        
        # Check by type analysis
        by_type = poll_stats['by_type']
        self.assertEqual(len(by_type), 2)  # Self and Híbrido
        
        # Find Self type stats
        self_stats = next((item for item in by_type if item['pollination_type__name'] == 'Self'), None)
        self.assertIsNotNone(self_stats)
        self.assertEqual(self_stats['count'], 2)  # 2 Self pollinations
        self.assertEqual(self_stats['total_capsules'], 12)  # 5 + 7
    
    def test_germination_statistics(self):
        """Test germination-specific statistics."""
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        germ_stats = self.statistics_service.germination_stats.get_statistics(parameters)
        
        # Check structure
        self.assertIn('summary', germ_stats)
        self.assertIn('by_responsible', germ_stats)
        self.assertIn('by_genus', germ_stats)
        self.assertIn('by_seed_source', germ_stats)
        self.assertIn('germination_rates', germ_stats)
        
        # Check summary
        summary = germ_stats['summary']
        self.assertEqual(summary['total_records'], 3)
        self.assertEqual(summary['total_seedlings'], 185)
        self.assertEqual(summary['total_seeds_planted'], 225)  # 100 + 50 + 75
        self.assertAlmostEqual(summary['overall_germination_rate'], 82.22, places=1)  # 185/225 * 100
        
        # Check germination rates
        rates = germ_stats['germination_rates']
        self.assertEqual(rates['records_analyzed'], 3)
        self.assertAlmostEqual(rates['overall_rate'], 82.22, places=1)
        self.assertEqual(rates['max_rate'], 85.0)  # 85/100 * 100
        self.assertEqual(rates['min_rate'], 80.0)  # 60/75 * 100
    
    def test_date_range_filtering(self):
        """Test filtering by date range."""
        # Test with narrow date range that excludes some records
        parameters = {
            'start_date': (date.today() - timedelta(days=20)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.statistics_service.get_comprehensive_statistics(parameters)
        
        # Should have fewer records due to date filtering
        summary = stats['summary']
        self.assertLess(summary['total_activities'], 6)
        
        # Check that recent records are included
        self.assertGreater(summary['pollination_records'], 0)
        self.assertGreater(summary['germination_records'], 0)
    
    def test_user_filtering(self):
        """Test filtering by responsible user."""
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat(),
            'responsible_id': str(self.admin_user.id)
        }
        
        stats = self.statistics_service.get_comprehensive_statistics(parameters)
        
        # Should only include admin user's records
        # Admin has 2 pollination records and 2 germination records
        summary = stats['summary']
        self.assertEqual(summary['pollination_records'], 2)
        self.assertEqual(summary['germination_records'], 2)
        self.assertEqual(summary['total_activities'], 4)
    
    def test_comparative_analysis(self):
        """Test comparative analysis between pollination and germination."""
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.statistics_service.get_comprehensive_statistics(parameters)
        comparative = stats['comparative']
        
        # Check structure
        self.assertIn('activity_ratios', comparative)
        self.assertIn('efficiency_metrics', comparative)
        self.assertIn('resource_utilization', comparative)
        
        # Check ratios
        ratios = comparative['activity_ratios']
        self.assertEqual(ratios['pollination_to_germination'], 1.0)  # 3/3
        
        # Check efficiency metrics
        efficiency = comparative['efficiency_metrics']
        self.assertEqual(efficiency['avg_capsules_per_pollination'], 5.0)
        self.assertAlmostEqual(efficiency['avg_seedlings_per_germination'], 61.67, places=1)
    
    def test_trend_analysis(self):
        """Test trend analysis functionality."""
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.statistics_service.get_comprehensive_statistics(parameters)
        trends = stats['trends']
        
        # Check structure
        self.assertIn('monthly_trends', trends)
        self.assertIn('weekly_trends', trends)
        self.assertIn('growth_rates', trends)
        self.assertIn('seasonal_patterns', trends)
        
        # Check that we have trend data
        self.assertIsInstance(trends['monthly_trends'], list)
        self.assertIsInstance(trends['weekly_trends'], list)
        
        # Check growth rates structure
        growth_rates = trends['growth_rates']
        self.assertIn('pollination_growth', growth_rates)
        self.assertIn('germination_growth', growth_rates)
        self.assertIn('overall_growth', growth_rates)
    
    def test_performance_statistics(self):
        """Test performance statistics functionality."""
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.statistics_service.get_comprehensive_statistics(parameters)
        performance = stats['performance']
        
        # Check structure
        self.assertIn('user_performance', performance)
        self.assertIn('species_performance', performance)
        self.assertIn('success_rates', performance)
        self.assertIn('productivity_metrics', performance)
        
        # Check user performance
        user_perf = performance['user_performance']
        self.assertIsInstance(user_perf, list)
        self.assertGreater(len(user_perf), 0)
        
        # Check that admin user appears in performance stats
        admin_stats = next((user for user in user_perf if user['username'] == 'admin'), None)
        self.assertIsNotNone(admin_stats)
        self.assertEqual(admin_stats['total_activities'], 4)  # 2 pollination + 2 germination
        
        # Check species performance
        species_perf = performance['species_performance']
        self.assertIsInstance(species_perf, list)
        self.assertGreater(len(species_perf), 0)
    
    def test_empty_data_handling(self):
        """Test handling of empty datasets."""
        # Delete all records
        PollinationRecord.objects.all().delete()
        GerminationRecord.objects.all().delete()
        
        parameters = {
            'start_date': (date.today() - timedelta(days=60)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.statistics_service.get_comprehensive_statistics(parameters)
        
        # Check that empty data is handled gracefully
        summary = stats['summary']
        self.assertEqual(summary['total_activities'], 0)
        self.assertEqual(summary['pollination_records'], 0)
        self.assertEqual(summary['germination_records'], 0)
        self.assertEqual(summary['total_capsules_produced'], 0)
        self.assertEqual(summary['total_seedlings_produced'], 0)


class StatisticsAPITest(APITestCase):
    """Test cases for Statistics API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users and roles
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Administrador del sistema',
            permissions={'can_generate_reports': True}
        )
        
        self.user_role = Role.objects.create(
            name='Polinizador',
            description='Usuario polinizador',
            permissions={'can_create_pollination': True}
        )
        
        self.admin_user = CustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.role = self.admin_role
        self.admin_user.save()
        
        self.regular_user = CustomUser.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.regular_user.role = self.user_role
        self.regular_user.save()
        
        # Create minimal test data
        self.plant = Plant.objects.create(
            genus='Test',
            species='species',
            vivero='Vivero A',
            mesa='Mesa 1',
            pared='Pared 1'
        )
        
        self.poll_type = PollinationType.objects.create(
            name='Self',
            description='Test type',
            requires_father_plant=False
        )
        
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0
        )
        
        # Create a test record
        PollinationRecord.objects.create(
            responsible=self.admin_user,
            pollination_type=self.poll_type,
            pollination_date=date.today() - timedelta(days=10),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
    
    def test_comprehensive_statistics_endpoint(self):
        """Test comprehensive statistics endpoint."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:statistics-comprehensive-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('summary', data)
        self.assertIn('pollination', data)
        self.assertIn('germination', data)
        self.assertIn('comparative', data)
        self.assertIn('trends', data)
        self.assertIn('performance', data)
        self.assertIn('metadata', data)
    
    def test_pollination_statistics_endpoint(self):
        """Test pollination statistics endpoint."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:statistics-pollination-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('pollination_statistics', data)
        self.assertIn('metadata', data)
        
        poll_stats = data['pollination_statistics']
        self.assertIn('summary', poll_stats)
        self.assertIn('by_type', poll_stats)
        self.assertIn('by_responsible', poll_stats)
    
    def test_germination_statistics_endpoint(self):
        """Test germination statistics endpoint."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:statistics-germination-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('germination_statistics', data)
        self.assertIn('metadata', data)
    
    def test_summary_statistics_endpoint(self):
        """Test summary statistics endpoint."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('reports:statistics-summary-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('summary', data)
        self.assertIn('recent_trends', data)
        self.assertIn('top_performers', data)
        self.assertIn('metadata', data)
    
    def test_performance_statistics_endpoint(self):
        """Test performance statistics endpoint."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:statistics-performance-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('user_performance', data)
        self.assertIn('species_performance', data)
        self.assertIn('success_rates', data)
        self.assertIn('productivity_metrics', data)
    
    def test_trends_statistics_endpoint(self):
        """Test trends statistics endpoint."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:statistics-trend-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('trends', data)
        self.assertIn('temporal_patterns', data)
        self.assertIn('metadata', data)
    
    def test_permission_denied_for_regular_user(self):
        """Test that regular users can't access detailed statistics."""
        self.client.force_authenticate(user=self.regular_user)
        
        # Test endpoints that require admin permissions
        endpoints = [
            'reports:statistics-comprehensive-statistics',
            'reports:statistics-pollination-statistics',
            'reports:statistics-germination-statistics',
            'reports:statistics-performance-statistics',
            'reports:statistics-trend-statistics'
        ]
        
        for endpoint in endpoints:
            url = reverse(endpoint)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users can't access statistics."""
        url = reverse('reports:statistics-comprehensive-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_query_parameters(self):
        """Test statistics endpoints with query parameters."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:statistics-comprehensive-statistics')
        params = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'responsible_id': str(self.admin_user.id)
        }
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        # Check that filters were applied in metadata
        self.assertIn('filters_applied', data['metadata'])
        filters = data['metadata']['filters_applied']
        self.assertEqual(filters['start_date'], '2024-01-01')
        self.assertEqual(filters['end_date'], '2024-12-31')
        self.assertEqual(filters['responsible_id'], str(self.admin_user.id))
    
    @patch('reports.statistics_services.StatisticsService.get_comprehensive_statistics')
    def test_error_handling(self, mock_stats):
        """Test error handling in statistics endpoints."""
        # Mock an exception
        mock_stats.side_effect = Exception("Test error")
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:statistics-comprehensive-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Test error', data['error'])


class PollinationStatisticsServiceTest(TestCase):
    """Test cases for PollinationStatisticsService."""
    
    def setUp(self):
        """Set up test data."""
        # Create minimal test data
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.plant = Plant.objects.create(
            genus='Test',
            species='species',
            vivero='Vivero A',
            mesa='Mesa 1',
            pared='Pared 1'
        )
        
        self.poll_type = PollinationType.objects.create(
            name='Self',
            description='Test type',
            requires_father_plant=False
        )
        
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0
        )
        
        self.service = PollinationStatisticsService()
    
    def test_empty_dataset_handling(self):
        """Test handling of empty pollination dataset."""
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        stats = self.service.get_statistics(parameters)
        
        # Check that empty data is handled gracefully
        summary = stats['summary']
        self.assertEqual(summary['total_records'], 0)
        self.assertEqual(summary['total_capsules'], 0)
        self.assertEqual(summary['avg_capsules_per_record'], 0)
        self.assertEqual(summary['success_rate'], 0)
    
    def test_single_record_statistics(self):
        """Test statistics with a single record."""
        PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.poll_type,
            pollination_date=date.today() - timedelta(days=10),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5
        )
        
        parameters = {
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.service.get_statistics(parameters)
        
        summary = stats['summary']
        self.assertEqual(summary['total_records'], 1)
        self.assertEqual(summary['total_capsules'], 5)
        self.assertEqual(summary['avg_capsules_per_record'], 5.0)
        self.assertEqual(summary['success_rate'], 100.0)


class GerminationStatisticsServiceTest(TestCase):
    """Test cases for GerminationStatisticsService."""
    
    def setUp(self):
        """Set up test data."""
        # Create minimal test data
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.plant = Plant.objects.create(
            genus='Test',
            species='species',
            vivero='Vivero A',
            mesa='Mesa 1',
            pared='Pared 1'
        )
        
        self.seed_source = SeedSource.objects.create(
            name='Test Source',
            source_type='Autopolinización',
            description='Test source'
        )
        
        self.germ_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Lab A'
        )
        
        self.service = GerminationStatisticsService()
    
    def test_empty_dataset_handling(self):
        """Test handling of empty germination dataset."""
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        stats = self.service.get_statistics(parameters)
        
        # Check that empty data is handled gracefully
        summary = stats['summary']
        self.assertEqual(summary['total_records'], 0)
        self.assertEqual(summary['total_seedlings'], 0)
        self.assertEqual(summary['total_seeds_planted'], 0)
        self.assertEqual(summary['overall_germination_rate'], 0)
    
    def test_germination_rate_calculation(self):
        """Test germination rate calculation."""
        GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today() - timedelta(days=10),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_setup=self.germ_setup,
            seeds_planted=100,
            seedlings_germinated=80
        )
        
        parameters = {
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat()
        }
        
        stats = self.service.get_statistics(parameters)
        
        summary = stats['summary']
        self.assertEqual(summary['total_records'], 1)
        self.assertEqual(summary['total_seedlings'], 80)
        self.assertEqual(summary['total_seeds_planted'], 100)
        self.assertEqual(summary['overall_germination_rate'], 80.0)
        
        # Check germination rates analysis
        rates = stats['germination_rates']
        self.assertEqual(rates['average_rate'], 80.0)
        self.assertEqual(rates['min_rate'], 80.0)
        self.assertEqual(rates['max_rate'], 80.0)
        self.assertEqual(rates['overall_rate'], 80.0)
        self.assertEqual(rates['records_analyzed'], 1)