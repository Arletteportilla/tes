from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from .models import ReportType, Report

User = get_user_model()


class ReportTypeModelTest(TestCase):
    """
    Test cases for ReportType model.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.report_type_data = {
            'name': 'pollination',
            'display_name': 'Reporte de Polinización',
            'description': 'Reporte detallado de procesos de polinización',
            'is_active': True
        }
    
    def test_create_report_type(self):
        """
        Test creating a ReportType instance.
        """
        report_type = ReportType.objects.create(**self.report_type_data)
        
        self.assertEqual(report_type.name, 'pollination')
        self.assertEqual(report_type.display_name, 'Reporte de Polinización')
        self.assertTrue(report_type.is_active)
        self.assertIsNotNone(report_type.created_at)
        self.assertIsNotNone(report_type.updated_at)
    
    def test_report_type_str_representation(self):
        """
        Test string representation of ReportType.
        """
        report_type = ReportType.objects.create(**self.report_type_data)
        self.assertEqual(str(report_type), 'Reporte de Polinización')
    
    def test_report_type_choices_validation(self):
        """
        Test that only valid choices are accepted for name field.
        """
        valid_choices = ['pollination', 'germination', 'statistical']
        
        for choice in valid_choices:
            report_type = ReportType(
                name=choice,
                display_name=f'Test {choice}',
                is_active=True
            )
            # Should not raise validation error
            report_type.full_clean()
    
    def test_get_default_template(self):
        """
        Test get_default_template method.
        """
        report_type = ReportType.objects.create(**self.report_type_data)
        expected_template = 'reports/pollination_report.html'
        self.assertEqual(report_type.get_default_template(), expected_template)
    
    def test_auto_set_template_name_on_save(self):
        """
        Test that template_name is automatically set if not provided.
        """
        report_type = ReportType.objects.create(**self.report_type_data)
        expected_template = 'reports/pollination_report.html'
        self.assertEqual(report_type.template_name, expected_template)
    
    def test_custom_template_name_preserved(self):
        """
        Test that custom template_name is preserved.
        """
        custom_template = 'custom/template.html'
        data = self.report_type_data.copy()
        data['template_name'] = custom_template
        
        report_type = ReportType.objects.create(**data)
        self.assertEqual(report_type.template_name, custom_template)
    
    def test_unique_name_constraint(self):
        """
        Test that name field must be unique.
        """
        ReportType.objects.create(**self.report_type_data)
        
        # Try to create another with same name
        with self.assertRaises(Exception):  # IntegrityError
            ReportType.objects.create(**self.report_type_data)


class ReportModelTest(TestCase):
    """
    Test cases for Report model.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create report type
        self.report_type = ReportType.objects.create(
            name='pollination',
            display_name='Reporte de Polinización',
            is_active=True
        )
        
        self.report_data = {
            'title': 'Reporte de Prueba',
            'report_type': self.report_type,
            'generated_by': self.user,
            'status': 'pending',
            'format': 'pdf',
            'parameters': {'start_date': '2024-01-01', 'end_date': '2024-01-31'}
        }
    
    def test_create_report(self):
        """
        Test creating a Report instance.
        """
        report = Report.objects.create(**self.report_data)
        
        self.assertEqual(report.title, 'Reporte de Prueba')
        self.assertEqual(report.report_type, self.report_type)
        self.assertEqual(report.generated_by, self.user)
        self.assertEqual(report.status, 'pending')
        self.assertEqual(report.format, 'pdf')
        self.assertIsNotNone(report.created_at)
        self.assertIsNotNone(report.updated_at)
    
    def test_report_str_representation(self):
        """
        Test string representation of Report.
        """
        report = Report.objects.create(**self.report_data)
        expected_str = f"{report.title} - {report.get_status_display()}"
        self.assertEqual(str(report), expected_str)
    
    def test_get_file_name_with_file_path(self):
        """
        Test get_file_name method when file_path is set.
        """
        report = Report.objects.create(**self.report_data)
        report.file_path = '/path/to/report_file.pdf'
        
        self.assertEqual(report.get_file_name(), 'report_file.pdf')
    
    def test_get_file_name_without_file_path(self):
        """
        Test get_file_name method when file_path is not set.
        """
        report = Report.objects.create(**self.report_data)
        file_name = report.get_file_name()
        
        # Should contain title and timestamp
        self.assertIn('Reporte de Prueba', file_name)
        self.assertTrue(file_name.endswith('.pdf'))
    
    def test_get_generation_duration(self):
        """
        Test get_generation_duration method.
        """
        report = Report.objects.create(**self.report_data)
        
        # No duration when times are not set
        self.assertIsNone(report.get_generation_duration())
        
        # Set times
        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=30)
        report.generation_started_at = start_time
        report.generation_completed_at = end_time
        
        self.assertEqual(report.get_generation_duration(), 30.0)
    
    def test_is_completed(self):
        """
        Test is_completed method.
        """
        report = Report.objects.create(**self.report_data)
        
        # Initially not completed
        self.assertFalse(report.is_completed())
        
        # Mark as completed
        report.status = 'completed'
        self.assertTrue(report.is_completed())
    
    def test_is_failed(self):
        """
        Test is_failed method.
        """
        report = Report.objects.create(**self.report_data)
        
        # Initially not failed
        self.assertFalse(report.is_failed())
        
        # Mark as failed
        report.status = 'failed'
        self.assertTrue(report.is_failed())
    
    def test_mark_as_generating(self):
        """
        Test mark_as_generating method.
        """
        report = Report.objects.create(**self.report_data)
        
        # Mark as generating
        report.mark_as_generating()
        
        # Refresh from database
        report.refresh_from_db()
        
        self.assertEqual(report.status, 'generating')
        self.assertIsNotNone(report.generation_started_at)
    
    def test_mark_as_completed(self):
        """
        Test mark_as_completed method.
        """
        report = Report.objects.create(**self.report_data)
        file_path = '/path/to/completed_report.pdf'
        file_size = 1024
        
        # Mark as completed
        report.mark_as_completed(file_path=file_path, file_size=file_size)
        
        # Refresh from database
        report.refresh_from_db()
        
        self.assertEqual(report.status, 'completed')
        self.assertEqual(report.file_path, file_path)
        self.assertEqual(report.file_size, file_size)
        self.assertIsNotNone(report.generation_completed_at)
    
    def test_mark_as_failed(self):
        """
        Test mark_as_failed method.
        """
        report = Report.objects.create(**self.report_data)
        error_message = 'Test error message'
        
        # Mark as failed
        report.mark_as_failed(error_message=error_message)
        
        # Refresh from database
        report.refresh_from_db()
        
        self.assertEqual(report.status, 'failed')
        self.assertEqual(report.error_message, error_message)
        self.assertIsNotNone(report.generation_completed_at)
    
    def test_report_status_choices(self):
        """
        Test that only valid status choices are accepted.
        """
        valid_statuses = ['pending', 'generating', 'completed', 'failed']
        
        for status in valid_statuses:
            report_data = self.report_data.copy()
            report_data['status'] = status
            report_data['metadata'] = {}  # Provide default for JSONField
            report = Report(**report_data)
            # Should not raise validation error
            report.full_clean()
    
    def test_report_format_choices(self):
        """
        Test that only valid format choices are accepted.
        """
        valid_formats = ['pdf', 'excel', 'json']
        
        for format_choice in valid_formats:
            report_data = self.report_data.copy()
            report_data['format'] = format_choice
            report_data['metadata'] = {}  # Provide default for JSONField
            report = Report(**report_data)
            # Should not raise validation error
            report.full_clean()
    
    def test_report_cascade_delete_user(self):
        """
        Test that reports are deleted when user is deleted.
        """
        report = Report.objects.create(**self.report_data)
        report_id = report.id
        
        # Delete user
        self.user.delete()
        
        # Report should be deleted
        with self.assertRaises(Report.DoesNotExist):
            Report.objects.get(id=report_id)
    
    def test_report_cascade_delete_report_type(self):
        """
        Test that reports are deleted when report type is deleted.
        """
        report = Report.objects.create(**self.report_data)
        report_id = report.id
        
        # Delete report type
        self.report_type.delete()
        
        # Report should be deleted
        with self.assertRaises(Report.DoesNotExist):
            Report.objects.get(id=report_id)
    
    def test_report_metadata_json_field(self):
        """
        Test that metadata JSON field works correctly.
        """
        metadata = {
            'total_records': 100,
            'filters_applied': ['date_range', 'status'],
            'generation_settings': {'include_charts': True}
        }
        
        report_data = self.report_data.copy()
        report_data['metadata'] = metadata
        
        report = Report.objects.create(**report_data)
        
        # Refresh from database
        report.refresh_from_db()
        
        self.assertEqual(report.metadata, metadata)
        self.assertEqual(report.metadata['total_records'], 100)
    
    def test_report_parameters_json_field(self):
        """
        Test that parameters JSON field works correctly.
        """
        parameters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'include_inactive': False,
            'group_by': 'month'
        }
        
        report_data = self.report_data.copy()
        report_data['parameters'] = parameters
        
        report = Report.objects.create(**report_data)
        
        # Refresh from database
        report.refresh_from_db()
        
        self.assertEqual(report.parameters, parameters)
        self.assertEqual(report.parameters['start_date'], '2024-01-01')
