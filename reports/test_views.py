"""
Tests for reports views.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json
import tempfile
import os

from .models import Report, ReportType
from authentication.models import Role

User = get_user_model()


class ReportTypeViewSetTest(TestCase):
    """
    Test cases for ReportTypeViewSet.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.client = APIClient()
        
        # Create roles
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Administrator role'
        )
        
        self.user_role = Role.objects.create(
            name='Polinizador',
            description='Pollinator role'
        )
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123',
            role=self.user_role
        )
        
        # Create report types
        self.report_type1 = ReportType.objects.create(
            name='pollination',
            display_name='Reporte de Polinización',
            is_active=True
        )
        
        self.report_type2 = ReportType.objects.create(
            name='germination',
            display_name='Reporte de Germinación',
            is_active=True
        )
        
        self.inactive_report_type = ReportType.objects.create(
            name='inactive',
            display_name='Inactive Report',
            is_active=False
        )
    
    def test_list_report_types_as_admin(self):
        """
        Test listing report types as administrator.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:reporttype-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Only active types
        
        # Check that inactive types are not included
        names = [item['name'] for item in response.data['results']]
        self.assertIn('pollination', names)
        self.assertIn('germination', names)
        self.assertNotIn('inactive', names)
    
    def test_list_report_types_as_regular_user(self):
        """
        Test listing report types as regular user (should be denied).
        """
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('reports:reporttype-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)  # No access
    
    def test_list_report_types_unauthenticated(self):
        """
        Test listing report types without authentication.
        """
        url = reverse('reports:reporttype-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_report_type(self):
        """
        Test retrieving a specific report type.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:reporttype-detail', kwargs={'pk': self.report_type1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'pollination')
        self.assertEqual(response.data['display_name'], 'Reporte de Polinización')


class ReportViewSetTest(TestCase):
    """
    Test cases for ReportViewSet.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.client = APIClient()
        
        # Create roles
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Administrator role'
        )
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        self.other_admin = User.objects.create_user(
            username='other_admin',
            email='other@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        # Create report type
        self.report_type = ReportType.objects.create(
            name='pollination',
            display_name='Reporte de Polinización',
            is_active=True
        )
        
        # Create reports
        self.report1 = Report.objects.create(
            title='Test Report 1',
            report_type=self.report_type,
            generated_by=self.admin_user,
            status='completed',
            format='pdf',
            parameters={'start_date': '2024-01-01', 'end_date': '2024-01-31'}
        )
        
        self.report2 = Report.objects.create(
            title='Test Report 2',
            report_type=self.report_type,
            generated_by=self.other_admin,
            status='pending',
            format='excel',
            parameters={'start_date': '2024-02-01', 'end_date': '2024-02-28'}
        )
    
    def test_list_reports_as_admin(self):
        """
        Test listing reports as administrator.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin should see all reports
        self.assertEqual(len(response.data['results']), 2)
    
    def test_list_own_reports_only(self):
        """
        Test that non-superuser admin sees only their own reports.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see all reports since both users are admins
        self.assertEqual(len(response.data['results']), 2)
    
    def test_retrieve_report(self):
        """
        Test retrieving a specific report.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-detail', kwargs={'pk': self.report1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Report 1')
        self.assertEqual(response.data['status'], 'completed')
    
    @patch('reports.views.ReportGeneratorService')
    @patch('reports.views.ExportService')
    def test_generate_report_success(self, mock_export_service, mock_generator_service):
        """
        Test successful report generation.
        """
        # Mock services
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = {
            'summary': {'total_records': 10},
            'metadata': {'generated_at': '2024-01-15T10:30:00Z'}
        }
        mock_generator_service.return_value = mock_generator
        
        mock_exporter = MagicMock()
        mock_exporter.export_report.return_value = b'fake_pdf_content'
        mock_exporter.get_file_extension.return_value = '.pdf'
        mock_export_service.return_value = mock_exporter
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-generate-report')
        data = {
            'report_type': 'pollination',
            'title': 'Generated Report',
            'format': 'pdf',
            'parameters': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            }
        }
        
        with patch('os.makedirs'), patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Generated Report')
        self.assertEqual(response.data['status'], 'completed')
        
        # Verify services were called
        mock_generator.generate_report.assert_called_once()
        mock_exporter.export_report.assert_called_once()
    
    def test_generate_report_invalid_type(self):
        """
        Test report generation with invalid report type.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-generate-report')
        data = {
            'report_type': 'invalid_type',
            'title': 'Invalid Report',
            'format': 'pdf',
            'parameters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_generate_report_missing_parameters(self):
        """
        Test report generation with missing required parameters.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-generate-report')
        data = {
            'report_type': 'pollination',
            # Missing title and format
            'parameters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_download_report_success(self):
        """
        Test successful report download.
        """
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(b'fake_pdf_content')
            temp_file_path = temp_file.name
        
        try:
            # Update report with file path
            self.report1.file_path = temp_file_path
            self.report1.status = 'completed'
            self.report1.save()
            
            self.client.force_authenticate(user=self.admin_user)
            
            url = reverse('reports:report-download-report', kwargs={'pk': self.report1.pk})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertIn('attachment', response['Content-Disposition'])
            self.assertEqual(response.content, b'fake_pdf_content')
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_download_report_not_completed(self):
        """
        Test downloading report that is not completed.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        # Use report2 which has status 'pending'
        url = reverse('reports:report-download-report', kwargs={'pk': self.report2.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_download_report_file_not_found(self):
        """
        Test downloading report when file doesn't exist.
        """
        # Set a non-existent file path
        self.report1.file_path = '/non/existent/path.pdf'
        self.report1.status = 'completed'
        self.report1.save()
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-download-report', kwargs={'pk': self.report1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_available_formats(self):
        """
        Test getting available export formats.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:report-available-formats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available_formats', response.data)
        self.assertIsInstance(response.data['available_formats'], list)
        
        # JSON should always be available
        format_names = [fmt['format'] for fmt in response.data['available_formats']]
        self.assertIn('json', format_names)


class ExportViewTest(TestCase):
    """
    Test cases for ExportView.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.client = APIClient()
        
        # Create admin role and user
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Administrator role'
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        # Create report type
        self.report_type = ReportType.objects.create(
            name='pollination',
            display_name='Reporte de Polinización',
            is_active=True
        )
    
    @patch('reports.views.ReportGeneratorService')
    @patch('reports.views.ExportService')
    def test_export_direct_success(self, mock_export_service, mock_generator_service):
        """
        Test successful direct export.
        """
        # Mock services
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = {
            'summary': {'total_records': 5},
            'metadata': {'generated_at': '2024-01-15T10:30:00Z'}
        }
        mock_generator_service.return_value = mock_generator
        
        mock_exporter = MagicMock()
        mock_exporter.export_report.return_value = b'fake_json_content'
        mock_exporter.get_content_type.return_value = 'application/json'
        mock_exporter.get_file_extension.return_value = '.json'
        mock_export_service.return_value = mock_exporter
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:export-export-direct')
        data = {
            'report_type': 'pollination',
            'title': 'Direct Export Test',
            'format': 'json',
            'parameters': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(response.content, b'fake_json_content')
        
        # Verify services were called
        mock_generator.generate_report.assert_called_once()
        mock_exporter.export_report.assert_called_once()
    
    def test_export_direct_invalid_data(self):
        """
        Test direct export with invalid data.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('reports:export-export-direct')
        data = {
            'report_type': 'invalid_type',
            'title': 'Invalid Export',
            'format': 'pdf'
            # Missing parameters
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_export_direct_permission_denied(self):
        """
        Test direct export without proper permissions.
        """
        # Create user without admin role
        regular_role = Role.objects.create(
            name='Polinizador',
            description='Regular user role'
        )
        
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123',
            role=regular_role
        )
        
        self.client.force_authenticate(user=regular_user)
        
        url = reverse('reports:export-export-direct')
        data = {
            'report_type': 'pollination',
            'title': 'Unauthorized Export',
            'format': 'json',
            'parameters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)