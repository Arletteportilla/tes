"""
Tests for report generation services.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from .models import Report, ReportType
from .services import (
    ReportGeneratorService,
    PollinationReportGenerator,
    GerminationReportGenerator,
    StatisticalReportGenerator
)
from pollination.models import PollinationRecord, PollinationType, Plant, ClimateCondition
from germination.models import GerminationRecord, SeedSource, GerminationCondition

User = get_user_model()


class ReportGeneratorServiceTest(TestCase):
    """
    Test cases for ReportGeneratorService.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.service = ReportGeneratorService()
        
        # Create user and report type
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.report_type = ReportType.objects.create(
            name='pollination',
            display_name='Reporte de Polinización',
            is_active=True
        )
        
        self.report = Report.objects.create(
            title='Test Report',
            report_type=self.report_type,
            generated_by=self.user,
            parameters={'start_date': '2024-01-01', 'end_date': '2024-01-31'}
        )
    
    def test_get_available_report_types(self):
        """
        Test getting available report types.
        """
        types = self.service.get_available_report_types()
        expected_types = ['pollination', 'germination', 'statistical']
        
        self.assertEqual(set(types), set(expected_types))
    
    def test_generate_report_pollination(self):
        """
        Test generating a pollination report.
        """
        with patch.object(PollinationReportGenerator, 'generate') as mock_generate:
            mock_generate.return_value = {'test': 'data'}
            
            result = self.service.generate_report(self.report)
            
            mock_generate.assert_called_once_with(self.report.parameters)
            self.assertEqual(result, {'test': 'data'})
    
    def test_generate_report_unsupported_type(self):
        """
        Test generating report with unsupported type.
        """
        # Create report type with unsupported name
        unsupported_type = ReportType.objects.create(
            name='unsupported',
            display_name='Unsupported Type',
            is_active=True
        )
        
        report = Report.objects.create(
            title='Unsupported Report',
            report_type=unsupported_type,
            generated_by=self.user,
            parameters={}
        )
        
        with self.assertRaises(ValueError) as context:
            self.service.generate_report(report)
        
        self.assertIn('Unsupported report type', str(context.exception))


class PollinationReportGeneratorTest(TestCase):
    """
    Test cases for PollinationReportGenerator.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.generator = PollinationReportGenerator()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test data
        self.pollination_type = PollinationType.objects.create(
            name='Self',
            description='Autopolinización test'
        )
        
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='test_species',
            vivero='Test Vivero',
            mesa='Mesa 1',
            pared='Pared A'
        )
        
        self.climate = ClimateCondition.objects.create(
            weather='Soleado',
            temperature=25.0,
            humidity=60
        )
        
        # Create pollination records
        self.record1 = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date(2024, 1, 15),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=5,
            estimated_maturation_date=date(2024, 4, 15)
        )
        
        self.record2 = PollinationRecord.objects.create(
            responsible=self.user,
            pollination_type=self.pollination_type,
            pollination_date=date(2024, 1, 20),
            mother_plant=self.plant,
            new_plant=self.plant,
            climate_condition=self.climate,
            capsules_quantity=3,
            estimated_maturation_date=date(2024, 4, 20)
        )
    
    def test_generate_basic_report(self):
        """
        Test generating basic pollination report.
        """
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        
        result = self.generator.generate(parameters)
        
        # Check structure
        self.assertIn('summary', result)
        self.assertIn('by_type', result)
        self.assertIn('by_responsible', result)
        self.assertIn('by_genus', result)
        self.assertIn('by_month', result)
        self.assertIn('success_rates', result)
        self.assertIn('records', result)
        self.assertIn('metadata', result)
        
        # Check summary data
        summary = result['summary']
        self.assertEqual(summary['total_records'], 2)
        self.assertGreater(summary['total_capsules'], 0)
    
    def test_generate_with_filters(self):
        """
        Test generating report with filters.
        """
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'responsible_id': self.user.id,
            'pollination_type': 'Self',
            'genus': 'Orchidaceae'
        }
        
        result = self.generator.generate(parameters)
        
        # Should still find our records
        self.assertEqual(result['summary']['total_records'], 2)
        
        # Check that filters are recorded in metadata
        self.assertEqual(result['metadata']['filters_applied'], parameters)
    
    def test_parse_date_range_string_dates(self):
        """
        Test parsing date range from string parameters.
        """
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        
        start_date, end_date = self.generator.parse_date_range(parameters)
        
        self.assertEqual(start_date, date(2024, 1, 1))
        self.assertEqual(end_date, date(2024, 1, 31))
    
    def test_parse_date_range_no_dates(self):
        """
        Test parsing date range when no dates provided (should default to last 30 days).
        """
        parameters = {}
        
        start_date, end_date = self.generator.parse_date_range(parameters)
        
        # Should be approximately 30 days ago to today
        expected_end = timezone.now().date()
        expected_start = expected_end - timedelta(days=30)
        
        self.assertEqual(end_date, expected_end)
        self.assertEqual(start_date, expected_start)
    
    def test_format_percentage(self):
        """
        Test percentage formatting.
        """
        # Normal case
        result = self.generator.format_percentage(25, 100)
        self.assertEqual(result, 25.0)
        
        # Zero total case
        result = self.generator.format_percentage(10, 0)
        self.assertEqual(result, 0.0)
        
        # Decimal case
        result = self.generator.format_percentage(1, 3)
        self.assertEqual(result, 33.33)
    
    def test_generate_by_type_analysis(self):
        """
        Test generating analysis by pollination type.
        """
        # Use the queryset from our test data
        queryset = PollinationRecord.objects.all()
        
        result = self.generator._generate_by_type_analysis(queryset)
        
        self.assertEqual(len(result), 1)  # Only one type in test data
        self.assertEqual(result[0]['type'], 'Self')
        self.assertEqual(result[0]['count'], 2)
        self.assertEqual(result[0]['percentage'], 100.0)
    
    def test_generate_success_rates(self):
        """
        Test generating success rates.
        """
        queryset = PollinationRecord.objects.all()
        
        result = self.generator._generate_success_rates(queryset)
        
        self.assertEqual(result['total_records'], 2)
        self.assertEqual(result['successful_records'], 2)  # Both have capsules > 0
        self.assertEqual(result['success_rate'], 100.0)


class GerminationReportGeneratorTest(TestCase):
    """
    Test cases for GerminationReportGenerator.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.generator = GerminationReportGenerator()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test data
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='test_species',
            vivero='Test Vivero',
            mesa='Mesa 1',
            pared='Pared A'
        )
        
        self.seed_source = SeedSource.objects.create(
            name='autopolinizacion',
            source_type='Autopolinización',
            description='Test Source'
        )
        
        self.germination_condition = GerminationCondition.objects.create(
            climate='Controlado',
            substrate='Turba',
            location='Test Location',
            temperature=25.0,
            humidity=70
        )
        
        # Create germination records
        self.record1 = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date(2024, 1, 15),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=15,
            seedlings_germinated=10,
            estimated_transplant_date=date(2024, 3, 15)
        )
        
        self.record2 = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date(2024, 1, 20),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=12,
            seedlings_germinated=8,
            estimated_transplant_date=date(2024, 3, 20)
        )
    
    def test_generate_basic_report(self):
        """
        Test generating basic germination report.
        """
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        
        result = self.generator.generate(parameters)
        
        # Check structure
        self.assertIn('summary', result)
        self.assertIn('by_responsible', result)
        self.assertIn('by_genus', result)
        self.assertIn('by_seed_source', result)
        self.assertIn('by_month', result)
        self.assertIn('success_rates', result)
        self.assertIn('records', result)
        self.assertIn('metadata', result)
        
        # Check summary data
        summary = result['summary']
        self.assertEqual(summary['total_records'], 2)
        self.assertGreater(summary['total_seedlings'], 0)
    
    def test_generate_with_filters(self):
        """
        Test generating report with filters.
        """
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'responsible_id': self.user.id,
            'genus': 'Orchidaceae',
            'seed_source': 'autopolinizacion'
        }
        
        result = self.generator.generate(parameters)
        
        # Should still find our records
        self.assertEqual(result['summary']['total_records'], 2)
        
        # Check that filters are recorded in metadata
        self.assertEqual(result['metadata']['filters_applied'], parameters)


class StatisticalReportGeneratorTest(TestCase):
    """
    Test cases for StatisticalReportGenerator.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.generator = StatisticalReportGenerator()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_generate_basic_report(self):
        """
        Test generating basic statistical report.
        """
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        
        result = self.generator.generate(parameters)
        
        # Check structure
        self.assertIn('summary', result)
        self.assertIn('pollination_stats', result)
        self.assertIn('germination_stats', result)
        self.assertIn('comparative_analysis', result)
        self.assertIn('trends', result)
        self.assertIn('metadata', result)
        
        # Check that it handles empty data gracefully
        summary = result['summary']
        self.assertEqual(summary['total_activities'], 0)
    
    def test_generate_consolidated_summary(self):
        """
        Test generating consolidated summary.
        """
        pollination_data = {
            'total_records': 10,
            'total_capsules': 50,
            'avg_capsules': 5.0
        }
        
        germination_data = {
            'total_records': 15,
            'total_seedlings': 150,
            'avg_seedlings': 10.0
        }
        
        result = self.generator._generate_consolidated_summary(pollination_data, germination_data)
        
        self.assertEqual(result['total_activities'], 25)
        self.assertEqual(result['pollination_records'], 10)
        self.assertEqual(result['germination_records'], 15)
        self.assertEqual(result['pollination_percentage'], 40.0)
        self.assertEqual(result['germination_percentage'], 60.0)
    
    def test_generate_comparative_analysis(self):
        """
        Test generating comparative analysis.
        """
        pollination_data = {
            'total_records': 10,
            'avg_capsules': 5.0
        }
        
        germination_data = {
            'total_records': 20,
            'avg_seedlings': 8.0
        }
        
        result = self.generator._generate_comparative_analysis(pollination_data, germination_data)
        
        self.assertEqual(result['activity_ratio']['pollination_to_germination'], 0.5)
        self.assertEqual(result['activity_ratio']['germination_to_pollination'], 2.0)
        self.assertEqual(result['productivity_comparison']['avg_capsules_per_pollination'], 5.0)
        self.assertEqual(result['productivity_comparison']['avg_seedlings_per_germination'], 8.0)


class BaseReportGeneratorTest(TestCase):
    """
    Test cases for BaseReportGenerator functionality.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.generator = PollinationReportGenerator()  # Use concrete implementation
    
    def test_parse_date_range_with_date_objects(self):
        """
        Test parsing date range with date objects.
        """
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        
        parameters = {
            'start_date': start,
            'end_date': end
        }
        
        start_date, end_date = self.generator.parse_date_range(parameters)
        
        self.assertEqual(start_date, start)
        self.assertEqual(end_date, end)
    
    def test_format_percentage_edge_cases(self):
        """
        Test percentage formatting edge cases.
        """
        # Zero numerator
        result = self.generator.format_percentage(0, 100)
        self.assertEqual(result, 0.0)
        
        # Equal values
        result = self.generator.format_percentage(50, 50)
        self.assertEqual(result, 100.0)
        
        # Very small percentage
        result = self.generator.format_percentage(1, 1000)
        self.assertEqual(result, 0.1)