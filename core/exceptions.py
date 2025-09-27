"""
Custom exception classes for the pollination and germination system.
Provides specific exception types for different error scenarios.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class BaseBusinessError(Exception):
    """Base class for business logic errors."""
    
    def __init__(self, message, code=None, details=None):
        self.message = message
        self.code = code or 'business_error'
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseBusinessError):
    """Custom validation error for business rules."""
    
    def __init__(self, message, code=None, field=None, details=None):
        self.field = field
        super().__init__(message, code or 'validation_error', details)


class DuplicateRecordError(ValidationError):
    """Error raised when attempting to create duplicate records."""
    
    def __init__(self, message=None, model_name=None, fields=None):
        self.model_name = model_name
        self.fields = fields or []
        
        if not message:
            if model_name and fields:
                field_names = ", ".join(fields)
                message = f"Ya existe un registro de {model_name} con los mismos valores para: {field_names}"
            else:
                message = "Ya existe un registro similar"
        
        super().__init__(message, 'duplicate_record', field=None, details={
            'model_name': model_name,
            'fields': fields
        })


class PollinationError(BaseBusinessError):
    """Base class for pollination-related errors."""
    
    def __init__(self, message, code=None, pollination_type=None, details=None):
        self.pollination_type = pollination_type
        details = details or {}
        if pollination_type:
            details['pollination_type'] = pollination_type
        super().__init__(message, code or 'pollination_error', details)


class PlantCompatibilityError(PollinationError):
    """Error raised when plants are not compatible for pollination type."""
    
    def __init__(self, message, pollination_type=None, mother_plant=None, father_plant=None):
        self.mother_plant = mother_plant
        self.father_plant = father_plant
        
        details = {
            'mother_plant': str(mother_plant) if mother_plant else None,
            'father_plant': str(father_plant) if father_plant else None
        }
        
        super().__init__(message, 'plant_compatibility_error', pollination_type, details)


class InvalidPollinationTypeError(PollinationError):
    """Error raised when pollination type is invalid or not supported."""
    
    def __init__(self, pollination_type, valid_types=None):
        self.valid_types = valid_types or ['Self', 'Sibling', 'Híbrido']
        
        message = f"Tipo de polinización '{pollination_type}' no válido. Tipos válidos: {', '.join(self.valid_types)}"
        
        super().__init__(message, 'invalid_pollination_type', pollination_type, {
            'valid_types': self.valid_types
        })


class GerminationError(BaseBusinessError):
    """Base class for germination-related errors."""
    
    def __init__(self, message, code=None, germination_record=None, details=None):
        self.germination_record = germination_record
        details = details or {}
        if germination_record:
            details['germination_record_id'] = getattr(germination_record, 'id', None)
        super().__init__(message, code or 'germination_error', details)


class SeedSourceCompatibilityError(GerminationError):
    """Error raised when seed source is not compatible with plant."""
    
    def __init__(self, message, seed_source=None, plant=None):
        self.seed_source = seed_source
        self.plant = plant
        
        details = {
            'seed_source': str(seed_source) if seed_source else None,
            'plant': str(plant) if plant else None
        }
        
        super().__init__(message, 'seed_source_compatibility_error', None, details)


class InvalidSeedlingQuantityError(GerminationError):
    """Error raised when seedling quantity exceeds seeds planted."""
    
    def __init__(self, seeds_planted, seedlings_germinated):
        self.seeds_planted = seeds_planted
        self.seedlings_germinated = seedlings_germinated
        
        message = f"Las plántulas germinadas ({seedlings_germinated}) no pueden exceder las semillas sembradas ({seeds_planted})"
        
        super().__init__(message, 'invalid_seedling_quantity', None, {
            'seeds_planted': seeds_planted,
            'seedlings_germinated': seedlings_germinated
        })


class DateError(ValidationError):
    """Base class for date-related errors."""
    
    def __init__(self, message, code=None, date_value=None, field_name=None):
        self.date_value = date_value
        self.field_name = field_name
        
        super().__init__(message, code or 'date_error', field_name, {
            'date_value': str(date_value) if date_value else None,
            'field_name': field_name
        })


class FutureDateError(DateError):
    """Error raised when a date is in the future but shouldn't be."""
    
    def __init__(self, date_value, field_name="fecha"):
        message = f"La {field_name} no puede ser una fecha futura"
        super().__init__(message, 'future_date_not_allowed', date_value, field_name)


class InvalidDateRangeError(DateError):
    """Error raised when date range is invalid."""
    
    def __init__(self, start_date, end_date, start_field="fecha inicio", end_field="fecha fin"):
        self.start_date = start_date
        self.end_date = end_date
        self.start_field = start_field
        self.end_field = end_field
        
        message = f"La {start_field} no puede ser posterior a la {end_field}"
        
        super().__init__(message, 'invalid_date_range', None, None)
        self.details.update({
            'start_date': str(start_date) if start_date else None,
            'end_date': str(end_date) if end_date else None,
            'start_field': start_field,
            'end_field': end_field
        })


class PermissionError(BaseBusinessError):
    """Error raised when user doesn't have required permissions."""
    
    def __init__(self, message, required_permission=None, user=None):
        self.required_permission = required_permission
        self.user = user
        
        super().__init__(message, 'permission_denied', {
            'required_permission': required_permission,
            'user': str(user) if user else None
        })


class InsufficientPermissionsError(PermissionError):
    """Error raised when user has insufficient permissions for an action."""
    
    def __init__(self, action, required_role=None, user=None):
        self.action = action
        self.required_role = required_role
        
        if required_role:
            message = f"Se requiere rol '{required_role}' para realizar la acción: {action}"
        else:
            message = f"Permisos insuficientes para realizar la acción: {action}"
        
        super().__init__(message, required_role, user)
        self.details.update({
            'action': action,
            'required_role': required_role
        })


class AlertError(BaseBusinessError):
    """Base class for alert-related errors."""
    
    def __init__(self, message, code=None, alert_type=None, details=None):
        self.alert_type = alert_type
        details = details or {}
        if alert_type:
            details['alert_type'] = alert_type
        super().__init__(message, code or 'alert_error', details)


class AlertGenerationError(AlertError):
    """Error raised when alert generation fails."""
    
    def __init__(self, message, alert_type=None, record_id=None, reason=None):
        self.record_id = record_id
        self.reason = reason
        
        super().__init__(message, 'alert_generation_error', alert_type, {
            'record_id': record_id,
            'reason': reason
        })


class ReportError(BaseBusinessError):
    """Base class for report-related errors."""
    
    def __init__(self, message, code=None, report_type=None, details=None):
        self.report_type = report_type
        details = details or {}
        if report_type:
            details['report_type'] = report_type
        super().__init__(message, code or 'report_error', details)


class ReportGenerationError(ReportError):
    """Error raised when report generation fails."""
    
    def __init__(self, message, report_type=None, format_type=None, reason=None):
        self.format_type = format_type
        self.reason = reason
        
        super().__init__(message, 'report_generation_error', report_type, {
            'format_type': format_type,
            'reason': reason
        })


class ExportError(ReportError):
    """Error raised when export operation fails."""
    
    def __init__(self, message, export_format=None, reason=None):
        self.export_format = export_format
        self.reason = reason
        
        super().__init__(message, 'export_error', None, {
            'export_format': export_format,
            'reason': reason
        })


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that handles our custom exceptions.
    
    Args:
        exc: The exception instance
        context: The context in which the exception occurred
        
    Returns:
        Response: DRF Response object with error details
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Log the exception
    logger.error(f"Exception occurred: {exc}", exc_info=True, extra={
        'exception_type': type(exc).__name__,
        'context': context
    })
    
    # Handle our custom exceptions
    if isinstance(exc, BaseBusinessError):
        error_data = {
            'error': {
                'code': exc.code,
                'message': exc.message,
                'details': exc.details,
                'timestamp': None  # Will be set by middleware
            }
        }
        
        # Determine HTTP status code based on exception type
        if isinstance(exc, PermissionError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, DuplicateRecordError):
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        
        response = Response(error_data, status=status_code)
    
    # Handle Django validation errors
    elif isinstance(exc, DjangoValidationError):
        error_data = {
            'error': {
                'code': 'validation_error',
                'message': 'Los datos proporcionados no son válidos',
                'details': exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages},
                'timestamp': None
            }
        }
        response = Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
    # Add timestamp to all error responses
    if response is not None and 'error' in response.data:
        from datetime import datetime
        response.data['error']['timestamp'] = datetime.now().isoformat()
    
    return response


def handle_validation_errors(errors):
    """
    Convert validation errors to a consistent format.
    
    Args:
        errors: List of error messages or dict of field errors
        
    Returns:
        dict: Formatted error response
    """
    if isinstance(errors, list):
        return {
            'non_field_errors': errors
        }
    elif isinstance(errors, dict):
        return errors
    else:
        return {
            'non_field_errors': [str(errors)]
        }


def log_business_error(error, context=None):
    """
    Log business errors with appropriate level and context.
    
    Args:
        error: The business error instance
        context: Additional context information
    """
    context = context or {}
    
    log_data = {
        'error_type': type(error).__name__,
        'error_code': getattr(error, 'code', 'unknown'),
        'error_message': str(error),
        'error_details': getattr(error, 'details', {}),
        **context
    }
    
    # Log validation errors as warnings, others as errors
    if isinstance(error, ValidationError):
        logger.warning(f"Validation error: {error}", extra=log_data)
    else:
        logger.error(f"Business error: {error}", extra=log_data)