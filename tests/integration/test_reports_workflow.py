"""
Integration tests for complete reports generation workflow.
Tests the end-to-end process from report request to file generation and delivery.
"""
import pytest
import os
import tempfile
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from factories import (
    AdministradorUserFactory, PolinizadorUserFactory, GerminadorUserFactory,
    SelfPollinationRecordFactory, GerminationRecordFactory,
    ReportTypeFactory, CompletedReportFactory, PollinationReportFactory
)
from reports.models import Report, ReportType
from reports.services import ReportGeneratorService, StatisticsService
from reports.export_services import ExportService
from pollination.models import PollinationRecord
from germination.models import GerminationRecord

User = get_user_model()


@pytest.mark.django_db
class TestReportsWorkflowIntegration(TransactionTestCase):
    """Test complete reports workflow integration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.admin = AdministradorUserFactory()
        self.polinizador = PolinizadorUserFactory()
        self.germinador = GerminadorUserFactory()
        
        # Create report types
        self.pollination_type = ReportTypeFactory(name='pollination')
        self.germination_type = ReportTypeFactory(name='germination')
        self.statistical_type = ReportTypeFactory(name='statistical')
        
        self.report_service = ReportGeneratorService()
        self.export_service = ExportService()
        self.stats_service = StatisticsService()
        
        # Create test data
        self.create_test_data()

    def create_test_data(self):
        """Create test data for reports."""
        # Create pollination records with different dates and types
        date_range = [date.today() - timedelta(days=i*10) for i in range(6)]
        
        self.pollinations = []
        for i, poll_date in enumerate(date_range):
            pollination = SelfPollinationRecordFactory(
                responsible=self.polinizador,
                pollination_date=poll_date,
                capsules_quantity=i+1,
                is_successful=i % 2 == 0  # Alternate success/failure
            )
            self.pollinations.append(pollination)
        
        # Create germination records
        self.germinations = []
        for i, germ_date in enumerate(date_range):
            germination = GerminationRecordFactory(
                responsible=self.germinador,
                germination_date=germ_date,
                seeds_planted=20 + i*5,
                seedlings_germinated=15 + i*3,
                is_successful=i % 3 != 0  # Different success pattern
            )
            self.germinations.append(germination)

    def test_complete_pollination_report_workflow(self):
        """Test complete pollination report generation workflow."""
        self.client.force_authenticate(user=self.admin)
        
        # Step 1: Request pollination report via API
        report_data = {
            'title': 'Test Pollination Report',
            'report_type': self.pollination_type.id,
            'format': 'pdf',
            'parameters': {
                'date_from': (date.today() - timedelta(days=60)).isoformat(),
                'date_to': date.today().isoformat(),
                'pollination_types': ['Self'],
                'include_charts': True,
                'group_by': 'species'
            }
        }
        
        response = self.client.post('/api/reports/', report_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Verify report creation
        report_id = response.data['id']
        report = Report.objects.get(id=report_id)
        self.assertEqual(report.status, 'pending')
        self.assertEqual(report.generated_by, self.admin)
        self.assertEqual(report.report_type, self.pollination_type)
        
        # Step 3: Generate report content
        report_content = self.report_service.generate_pollination_report(
            report.parameters['date_from'],
            report.parameters['date_to'],
            report.parameters
        )
        
        # Verify report content structure
        self.assertIn('summary', report_content)
        self.assertIn('records', report_content)
        self.assertIn('statistics', report_content)
        
        # Step 4: Export report to PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            try:
                pdf_content = self.export_service.export_to_pdf(
                    report_content,
                    'pollination_report_template.html'
                )
                temp_file.write(pdf_content)
                temp_file.flush()
                
                # Verify PDF was created
                self.assertGreater(os.path.getsize(temp_file.name), 0)
                
                # Update report status
                report.status = 'completed'
                report.file_path = temp_file.name
                report.file_size = os.path.getsize(temp_file.name)
                report.generation_completed_at = timezone.now()
                report.save()
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        
        # Step 5: Verify completed report
        report.refresh_from_db()
        self.assertEqual(report.status, 'completed')
        self.assertIsNotNone(report.file_size)
        self.assertIsNotNone(report.generation_completed_at)

    def test_complete_germination_report_workflow(self):
        """Test complete germination report generation workflow."""
        self.client.force_authenticate(user=self.admin)
        
        # Step 1: Request germination report
        report_data = {
            'title': 'Test Germination Report',
            'report_type': self.germination_type.id,
            'format': 'excel',
            'parameters': {
                'date_from': (date.today() - timedelta(days=60)).isoformat(),
                'date_to': date.today().isoformat(),
                'include_success_rates': True,
                'include_charts': True,
                'group_by': 'species'
            }
        }
        
        response = self.client.post('/api/reports/', report_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Generate report content
        report = Report.objects.get(id=response.data['id'])
        report_content = self.report_service.generate_germination_report(
            report.parameters['date_from'],
            report.parameters['date_to'],
            report.parameters
        )
        
        # Verify germination-specific content
        self.assertIn('success_rates', report_content)
        self.assertIn('transplant_statistics', report_content)
        
        # Step 3: Export to Excel
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            try:
                excel_content = self.export_service.export_to_excel(
                    report_content,
                    'germination_report'
                )
                temp_file.write(excel_content)
                temp_file.flush()
                
                # Verify Excel file was created
                self.assertGreater(os.path.getsize(temp_file.name), 0)
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)

    def test_complete_statistical_report_workflow(self):
        """Test complete statistical report generation workflow."""
        self.client.force_authenticate(user=self.admin)
        
        # Step 1: Request statistical report
        report_data = {
            'title': 'Test Statistical Report',
            'report_type': self.statistical_type.id,
            'format': 'pdf',
            'parameters': {
                'date_from': (date.today() - timedelta(days=90)).isoformat(),
                'date_to': date.today().isoformat(),
                'include_pollination': True,
                'include_germination': True,
                'include_trends': True,
                'include_charts': True
            }
        }
        
        response = self.client.post('/api/reports/', report_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Generate comprehensive statistics
        report = Report.objects.get(id=response.data['id'])
        
        # Get pollination statistics
        pollination_stats = self.stats_service.get_pollination_statistics(
            report.parameters['date_from'],
            report.parameters['date_to']
        )
        
        # Get germination statistics
        germination_stats = self.stats_service.get_germination_statistics(
            report.parameters['date_from'],
            report.parameters['date_to']
        )
        
        # Get trend analysis
        trends = self.stats_service.get_trend_analysis(
            report.parameters['date_from'],
            report.parameters['date_to']
        )
        
        # Step 3: Verify statistical content
        self.assertIn('total_records', pollination_stats)
        self.assertIn('success_rate', pollination_stats)
        self.assertIn('by_species', pollination_stats)
        
        self.assertIn('total_records', germination_stats)
        self.assertIn('average_success_rate', germination_stats)
        self.assertIn('by_substrate', germination_stats)
        
        self.assertIn('monthly_trends', trends)
        self.assertIn('success_trends', trends)

    def test_report_workflow_with_filtering_and_grouping(self):
        """Test report workflow with advanced filtering and grouping."""
        self.client.force_authenticate(user=self.admin)
        
        # Step 1: Create report with specific filters
        report_data = {
            'title': 'Filtered Pollination Report',
            'report_type': self.pollination_type.id,
            'format': 'json',
            'parameters': {
                'date_from': (date.today() - timedelta(days=30)).isoformat(),
                'date_to': date.today().isoformat(),
                'pollination_types': ['Self'],
                'responsible_users': [self.polinizador.id],
                'success_only': True,
                'group_by': 'month',
                'include_charts': False
            }
        }
        
        response = self.client.post('/api/reports/', report_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Generate filtered report
        report = Report.objects.get(id=response.data['id'])
        filtered_content = self.report_service.generate_pollination_report(
            report.parameters['date_from'],
            report.parameters['date_to'],
            report.parameters
        )
        
        # Step 3: Verify filtering worked
        for record in filtered_content['records']:
            self.assertEqual(record['pollination_type'], 'Self')
            self.assertEqual(record['responsible_id'], self.polinizador.id)
            if 'is_successful' in record:
                self.assertTrue(record['is_successful'])

    def test_report_workflow_error_handling(self):
        """Test report workflow error handling."""
        self.client.force_authenticate(user=self.admin)
        
        # Step 1: Test invalid date range
        invalid_data = {
            'title': 'Invalid Report',
            'report_type': self.pollination_type.id,
            'format': 'pdf',
            'parameters': {
                'date_from': date.today().isoformat(),
                'date_to': (date.today() - timedelta(days=30)).isoformat(),  # End before start
            }
        }
        
        response = self.client.post('/api/reports/', invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 2: Test invalid report type
        invalid_type_data = {
            'title': 'Invalid Type Report',
            'report_type': 99999,  # Non-existent type
            'format': 'pdf',
            'parameters': {}
        }
        
        response = self.client.post('/api/reports/', invalid_type_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 3: Test unauthorized access (non-admin user)
        self.client.force_authenticate(user=self.polinizador)
        
        valid_data = {
            'title': 'Unauthorized Report',
            'report_type': self.pollination_type.id,
            'format': 'pdf',
            'parameters': {}
        }
        
        response = self.client.post('/api/reports/', valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_workflow_with_large_dataset(self):
        """Test report workflow performance with large dataset."""
        # Step 1: Create large dataset
        large_pollinations = [
            SelfPollinationRecordFactory(responsible=self.polinizador)
            for _ in range(100)
        ]
        large_germinations = [
            GerminationRecordFactory(responsible=self.germinador)
            for _ in range(100)
        ]
        
        self.client.force_authenticate(user=self.admin)
        
        # Step 2: Request large report
        report_data = {
            'title': 'Large Dataset Report',
            'report_type': self.statistical_type.id,
            'format': 'excel',
            'parameters': {
                'date_from': (date.today() - timedelta(days=365)).isoformat(),
                'date_to': date.today().isoformat(),
                'include_pollination': True,
                'include_germination': True,
                'include_trends': True
            }
        }
        
        import time
        start_time = time.time()
        
        response = self.client.post('/api/reports/', report_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 3: Generate report content
        report = Report.objects.get(id=response.data['id'])
        report_content = self.report_service.generate_statistical_report(
            report.parameters['date_from'],
            report.parameters['date_to'],
            report.parameters
        )
        
        generation_time = time.time() - start_time
        
        # Step 4: Verify performance is reasonable
        self.assertLess(generation_time, 30.0)  # Should complete within 30 seconds
        
        # Verify content includes large dataset
        self.assertGreaterEqual(
            report_content['pollination_summary']['total_records'],
            100
        )
        self.assertGreaterEqual(
            report_content['germination_summary']['total_records'],
            100
        )

    def test_report_workflow_export_formats(self):
        """Test report workflow with different export formats."""
        self.client.force_authenticate(user=self.admin)
        
        formats_to_test = ['pdf', 'excel', 'json']
        
        for format_type in formats_to_test:
            with self.subTest(format=format_type):
                # Step 1: Request report in specific format
                report_data = {
                    'title': f'Test {format_type.upper()} Report',
                    'report_type': self.pollination_type.id,
                    'format': format_type,
                    'parameters': {
                        'date_from': (date.today() - timedelta(days=30)).isoformat(),
                        'date_to': date.today().isoformat(),
                    }
                }
                
                response = self.client.post('/api/reports/', report_data)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                
                # Step 2: Generate and export report
                report = Report.objects.get(id=response.data['id'])
                report_content = self.report_service.generate_pollination_report(
                    report.parameters['date_from'],
                    report.parameters['date_to'],
                    report.parameters
                )
                
                # Step 3: Test export in specific format
                if format_type == 'pdf':
                    exported_content = self.export_service.export_to_pdf(
                        report_content,
                        'pollination_report_template.html'
                    )
                    self.assertIsInstance(exported_content, bytes)
                    
                elif format_type == 'excel':
                    exported_content = self.export_service.export_to_excel(
                        report_content,
                        'pollination_report'
                    )
                    self.assertIsInstance(exported_content, bytes)
                    
                elif format_type == 'json':
                    exported_content = self.export_service.export_to_json(
                        report_content
                    )
                    self.assertIsInstance(exported_content, (str, bytes))

    def test_report_workflow_scheduled_generation(self):
        """Test report workflow with scheduled generation."""
        # Step 1: Create scheduled report
        scheduled_report = Report.objects.create(
            title='Scheduled Weekly Report',
            report_type=self.statistical_type,
            generated_by=self.admin,
            status='scheduled',
            format='pdf',
            parameters={
                'date_from': (date.today() - timedelta(days=7)).isoformat(),
                'date_to': date.today().isoformat(),
                'include_pollination': True,
                'include_germination': True
            },
            scheduled_generation_date=timezone.now() + timedelta(hours=1)
        )
        
        # Step 2: Simulate scheduled generation trigger
        scheduled_reports = Report.objects.filter(
            status='scheduled',
            scheduled_generation_date__lte=timezone.now() + timedelta(hours=2)
        )
        
        self.assertEqual(scheduled_reports.count(), 1)
        
        # Step 3: Process scheduled report
        for report in scheduled_reports:
            report.status = 'generating'
            report.generation_started_at = timezone.now()
            report.save()
            
            # Generate content
            report_content = self.report_service.generate_statistical_report(
                report.parameters['date_from'],
                report.parameters['date_to'],
                report.parameters
            )
            
            # Mark as completed
            report.status = 'completed'
            report.generation_completed_at = timezone.now()
            report.save()
        
        # Step 4: Verify scheduled report was processed
        scheduled_report.refresh_from_db()
        self.assertEqual(scheduled_report.status, 'completed')
        self.assertIsNotNone(scheduled_report.generation_started_at)
        self.assertIsNotNone(scheduled_report.generation_completed_at)

    def test_report_workflow_access_control(self):
        """Test report workflow access control and permissions."""
        # Step 1: Test admin access (should work)
        self.client.force_authenticate(user=self.admin)
        
        admin_response = self.client.get('/api/reports/')
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        
        # Step 2: Test polinizador access (should be restricted)
        self.client.force_authenticate(user=self.polinizador)
        
        polinizador_response = self.client.get('/api/reports/')
        self.assertEqual(polinizador_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Step 3: Test germinador access (should be restricted)
        self.client.force_authenticate(user=self.germinador)
        
        germinador_response = self.client.get('/api/reports/')
        self.assertEqual(germinador_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Step 4: Test unauthenticated access
        unauthorized_client = APIClient()
        
        unauth_response = unauthorized_client.get('/api/reports/')
        self.assertEqual(unauth_response.status_code, status.HTTP_401_UNAUTHORIZED)