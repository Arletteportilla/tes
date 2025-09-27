"""
Tests for export services.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

from .export_services import ExportService, JSONExporter, BaseExporter
from .models import Report, ReportType

User = get_user_model()


class ExportServiceTest(TestCase):
    """
    Test cases for ExportService.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.service = ExportService()
        self.sample_report_data = {
            'summary': {
                'total_records': 10,
                'total_capsules': 50,
                'average_per_day': 2.5
            },
            'by_type': [
                {'type': 'Self', 'count': 5, 'percentage': 50.0, 'avg_capsules': 5.0},
                {'type': 'Sibling', 'count': 3, 'percentage': 30.0, 'avg_capsules': 4.0},
                {'type': 'Híbrido', 'count': 2, 'percentage': 20.0, 'avg_capsules': 6.0}
            ],
            'metadata': {
                'generated_at': '2024-01-15T10:30:00Z',
                'date_range': {
                    'start': '2024-01-01',
                    'end': '2024-01-31'
                },
                'total_records': 10
            }
        }
    
    def test_get_available_formats(self):
        """
        Test getting available export formats.
        """
        formats = self.service.get_available_formats()
        
        # JSON should always be available
        self.assertIn('json', formats)
        
        # Other formats depend on library availability
        self.assertIsInstance(formats, list)
        self.assertGreater(len(formats), 0)
    
    def test_get_content_type(self):
        """
        Test getting content type for formats.
        """
        self.assertEqual(self.service.get_content_type('json'), 'application/json')
        self.assertEqual(self.service.get_content_type('pdf'), 'application/pdf')
        self.assertEqual(self.service.get_content_type('excel'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertEqual(self.service.get_content_type('unknown'), 'application/octet-stream')
    
    def test_get_file_extension(self):
        """
        Test getting file extension for formats.
        """
        self.assertEqual(self.service.get_file_extension('json'), '.json')
        self.assertEqual(self.service.get_file_extension('pdf'), '.pdf')
        self.assertEqual(self.service.get_file_extension('excel'), '.xlsx')
        self.assertEqual(self.service.get_file_extension('unknown'), '.bin')
    
    def test_export_report_json(self):
        """
        Test exporting report in JSON format.
        """
        result = self.service.export_report(self.sample_report_data, 'json', 'Test Report')
        
        self.assertIsInstance(result, bytes)
        
        # Parse JSON to verify structure
        json_data = json.loads(result.decode('utf-8'))
        self.assertIn('title', json_data)
        self.assertIn('exported_at', json_data)
        self.assertIn('data', json_data)
        self.assertEqual(json_data['title'], 'Test Report')
        self.assertEqual(json_data['data'], self.sample_report_data)
    
    def test_export_report_unsupported_format(self):
        """
        Test exporting report with unsupported format.
        """
        with self.assertRaises(ValueError) as context:
            self.service.export_report(self.sample_report_data, 'unsupported', 'Test Report')
        
        self.assertIn('Unsupported export format', str(context.exception))


class JSONExporterTest(TestCase):
    """
    Test cases for JSONExporter.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.exporter = JSONExporter()
        self.sample_data = {
            'test_field': 'test_value',
            'number_field': 123,
            'nested_field': {
                'inner_field': 'inner_value'
            }
        }
    
    def test_export_json(self):
        """
        Test JSON export functionality.
        """
        result = self.exporter.export(self.sample_data, 'Test Title')
        
        self.assertIsInstance(result, bytes)
        
        # Parse and verify JSON structure
        json_data = json.loads(result.decode('utf-8'))
        
        self.assertEqual(json_data['title'], 'Test Title')
        self.assertIn('exported_at', json_data)
        self.assertEqual(json_data['data'], self.sample_data)
        
        # Verify exported_at is a valid ISO timestamp
        exported_at = json_data['exported_at']
        datetime.fromisoformat(exported_at.replace('Z', '+00:00'))  # Should not raise exception
    
    def test_export_json_with_special_characters(self):
        """
        Test JSON export with special characters.
        """
        data_with_special_chars = {
            'spanish_text': 'Polinización y germinación',
            'symbols': 'Test with symbols: áéíóú ñ ¿¡',
            'unicode': '🌱🌸'
        }
        
        result = self.exporter.export(data_with_special_chars, 'Test with Special Chars')
        
        # Should not raise exception and should preserve special characters
        json_data = json.loads(result.decode('utf-8'))
        self.assertEqual(json_data['data']['spanish_text'], 'Polinización y germinación')
        self.assertEqual(json_data['data']['symbols'], 'Test with symbols: áéíóú ñ ¿¡')


class BaseExporterTest(TestCase):
    """
    Test cases for BaseExporter utility methods.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        # Use JSONExporter as concrete implementation
        self.exporter = JSONExporter()
    
    def test_format_date_iso_string(self):
        """
        Test formatting ISO date string.
        """
        iso_date = '2024-01-15T10:30:00Z'
        result = self.exporter.format_date(iso_date)
        self.assertEqual(result, '15/01/2024')
    
    def test_format_date_iso_string_with_timezone(self):
        """
        Test formatting ISO date string with timezone.
        """
        iso_date = '2024-01-15T10:30:00+00:00'
        result = self.exporter.format_date(iso_date)
        self.assertEqual(result, '15/01/2024')
    
    def test_format_date_invalid_string(self):
        """
        Test formatting invalid date string.
        """
        invalid_date = 'not-a-date'
        result = self.exporter.format_date(invalid_date)
        self.assertEqual(result, 'not-a-date')
    
    def test_format_date_none(self):
        """
        Test formatting None date.
        """
        result = self.exporter.format_date(None)
        self.assertEqual(result, 'None')
    
    def test_format_number_integer(self):
        """
        Test formatting integer number.
        """
        result = self.exporter.format_number(42)
        self.assertEqual(result, '42')
    
    def test_format_number_float(self):
        """
        Test formatting float number.
        """
        result = self.exporter.format_number(42.567)
        self.assertEqual(result, '42.57')
    
    def test_format_number_string(self):
        """
        Test formatting string as number.
        """
        result = self.exporter.format_number('not-a-number')
        self.assertEqual(result, 'not-a-number')
    
    def test_format_number_none(self):
        """
        Test formatting None as number.
        """
        result = self.exporter.format_number(None)
        self.assertEqual(result, 'None')


class PDFExporterTest(TestCase):
    """
    Test cases for PDFExporter.
    Note: These tests will be skipped if ReportLab is not available.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.sample_data = {
            'summary': {
                'total_records': 10,
                'total_capsules': 50
            },
            'metadata': {
                'generated_at': '2024-01-15T10:30:00Z',
                'date_range': {
                    'start': '2024-01-01',
                    'end': '2024-01-31'
                },
                'total_records': 10
            }
        }
    
    @patch('reports.export_services.REPORTLAB_AVAILABLE', True)
    def test_pdf_exporter_import_error(self):
        """
        Test PDFExporter raises ImportError when ReportLab is not available.
        """
        with patch('reports.export_services.REPORTLAB_AVAILABLE', False):
            from .export_services import PDFExporter
            
            with self.assertRaises(ImportError) as context:
                PDFExporter()
            
            self.assertIn('ReportLab is required', str(context.exception))
    
    def test_pdf_exporter_available(self):
        """
        Test PDFExporter when ReportLab is available.
        """
        try:
            from .export_services import PDFExporter
            exporter = PDFExporter()
            
            # If we get here, ReportLab is available
            result = exporter.export(self.sample_data, 'Test PDF Report')
            
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)
            
            # PDF files start with %PDF
            self.assertTrue(result.startswith(b'%PDF'))
            
        except ImportError:
            # ReportLab not available, skip test
            self.skipTest("ReportLab not available")


class ExcelExporterTest(TestCase):
    """
    Test cases for ExcelExporter.
    Note: These tests will be skipped if openpyxl is not available.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.sample_data = {
            'summary': {
                'total_records': 10,
                'total_seedlings': 80
            },
            'by_type': [
                {'type': 'Self', 'count': 5, 'percentage': 50.0, 'avg_capsules': 5.0}
            ],
            'records': [
                {
                    'id': 1,
                    'date': '2024-01-15',
                    'responsible': 'testuser',
                    'type': 'Self'
                }
            ],
            'metadata': {
                'generated_at': '2024-01-15T10:30:00Z',
                'date_range': {
                    'start': '2024-01-01',
                    'end': '2024-01-31'
                },
                'total_records': 10
            }
        }
    
    @patch('reports.export_services.OPENPYXL_AVAILABLE', True)
    def test_excel_exporter_import_error(self):
        """
        Test ExcelExporter raises ImportError when openpyxl is not available.
        """
        with patch('reports.export_services.OPENPYXL_AVAILABLE', False):
            from .export_services import ExcelExporter
            
            with self.assertRaises(ImportError) as context:
                ExcelExporter()
            
            self.assertIn('openpyxl is required', str(context.exception))
    
    def test_excel_exporter_available(self):
        """
        Test ExcelExporter when openpyxl is available.
        """
        try:
            from .export_services import ExcelExporter
            exporter = ExcelExporter()
            
            # If we get here, openpyxl is available
            result = exporter.export(self.sample_data, 'Test Excel Report')
            
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)
            
            # Excel files start with PK (ZIP signature)
            self.assertTrue(result.startswith(b'PK'))
            
        except ImportError:
            # openpyxl not available, skip test
            self.skipTest("openpyxl not available")