"""
Serializers for the reports app.
Provides serialization for report models and API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Report, ReportType

User = get_user_model()


class ReportTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for ReportType model.
    """
    
    class Meta:
        model = ReportType
        fields = [
            'id',
            'name',
            'display_name',
            'description',
            'is_active',
            'template_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReportSerializer(serializers.ModelSerializer):
    """
    Serializer for Report model.
    """
    report_type_name = serializers.CharField(source='report_type.name', read_only=True)
    report_type_display = serializers.CharField(source='report_type.display_name', read_only=True)
    generated_by_username = serializers.CharField(source='generated_by.username', read_only=True)
    generated_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    file_name = serializers.CharField(source='get_file_name', read_only=True)
    generation_duration = serializers.CharField(source='get_generation_duration', read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    is_failed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id',
            'title',
            'report_type',
            'report_type_name',
            'report_type_display',
            'generated_by',
            'generated_by_username',
            'generated_by_name',
            'status',
            'status_display',
            'format',
            'format_display',
            'parameters',
            'file_path',
            'file_name',
            'file_size',
            'generation_started_at',
            'generation_completed_at',
            'generation_duration',
            'error_message',
            'metadata',
            'is_completed',
            'is_failed',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'generated_by',
            'status',
            'file_path',
            'file_size',
            'generation_started_at',
            'generation_completed_at',
            'error_message',
            'metadata',
            'created_at',
            'updated_at'
        ]
    
    def get_generated_by_name(self, obj):
        """
        Get the full name of the user who generated the report.
        """
        if obj.generated_by:
            full_name = obj.generated_by.get_full_name()
            return full_name if full_name else obj.generated_by.username
        return None


class ReportGenerationSerializer(serializers.Serializer):
    """
    Serializer for report generation requests.
    Validates parameters for generating new reports.
    """
    REPORT_TYPE_CHOICES = [
        ('pollination', 'Reporte de Polinización'),
        ('germination', 'Reporte de Germinación'),
        ('statistical', 'Reporte Estadístico'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]
    
    report_type = serializers.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        help_text="Tipo de reporte a generar"
    )
    title = serializers.CharField(
        max_length=200,
        help_text="Título del reporte"
    )
    format = serializers.ChoiceField(
        choices=FORMAT_CHOICES,
        default='pdf',
        help_text="Formato de exportación"
    )
    parameters = serializers.JSONField(
        default=dict,
        help_text="Parámetros para la generación del reporte"
    )
    
    def validate_parameters(self, value):
        """
        Validate report parameters based on report type.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Los parámetros deben ser un objeto JSON válido")
        
        # Basic validation - you can extend this based on specific requirements
        if 'start_date' in value or 'end_date' in value:
            start_date = value.get('start_date')
            end_date = value.get('end_date')
            
            if start_date and end_date:
                try:
                    from datetime import datetime
                    start = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end = datetime.strptime(end_date, '%Y-%m-%d').date()
                    
                    if start > end:
                        raise serializers.ValidationError(
                            "La fecha de inicio no puede ser posterior a la fecha de fin"
                        )
                except ValueError:
                    raise serializers.ValidationError(
                        "Las fechas deben estar en formato YYYY-MM-DD"
                    )
        
        return value
    
    def validate(self, data):
        """
        Cross-field validation.
        """
        # Validate that report type exists and is active
        try:
            report_type = ReportType.objects.get(name=data['report_type'], is_active=True)
        except ReportType.DoesNotExist:
            raise serializers.ValidationError({
                'report_type': f"Tipo de reporte no encontrado o inactivo: {data['report_type']}"
            })
        
        # Validate format availability
        from .export_services import ExportService
        export_service = ExportService()
        available_formats = export_service.get_available_formats()
        
        if data['format'] not in available_formats:
            raise serializers.ValidationError({
                'format': f"Formato no disponible: {data['format']}. Formatos disponibles: {', '.join(available_formats)}"
            })
        
        return data


class ReportSummarySerializer(serializers.ModelSerializer):
    """
    Simplified serializer for report summaries.
    Used for listing reports with minimal information.
    """
    report_type_name = serializers.CharField(source='report_type.name', read_only=True)
    generated_by_username = serializers.CharField(source='generated_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    is_completed = serializers.BooleanField(source='is_completed', read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id',
            'title',
            'report_type_name',
            'generated_by_username',
            'status',
            'status_display',
            'format',
            'format_display',
            'is_completed',
            'created_at'
        ]


class ReportParametersSerializer(serializers.Serializer):
    """
    Serializer for common report parameters.
    Provides validation for standard report parameters.
    """
    start_date = serializers.DateField(
        required=False,
        help_text="Fecha de inicio del período (YYYY-MM-DD)"
    )
    end_date = serializers.DateField(
        required=False,
        help_text="Fecha de fin del período (YYYY-MM-DD)"
    )
    responsible_id = serializers.IntegerField(
        required=False,
        help_text="ID del usuario responsable"
    )
    genus = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Filtrar por género de planta"
    )
    species = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Filtrar por especie de planta"
    )
    pollination_type = serializers.CharField(
        max_length=20,
        required=False,
        help_text="Filtrar por tipo de polinización"
    )
    seed_source = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Filtrar por fuente de semillas"
    )
    include_inactive = serializers.BooleanField(
        default=False,
        help_text="Incluir registros inactivos"
    )
    record_limit = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        help_text="Límite de registros detallados a incluir"
    )
    group_by = serializers.ChoiceField(
        choices=[
            ('day', 'Por día'),
            ('week', 'Por semana'),
            ('month', 'Por mes'),
            ('year', 'Por año')
        ],
        default='month',
        required=False,
        help_text="Agrupar datos por período"
    )
    
    def validate(self, data):
        """
        Cross-field validation for parameters.
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser posterior a la fecha de fin"
            )
        
        # Validate responsible_id if provided
        responsible_id = data.get('responsible_id')
        if responsible_id:
            try:
                User.objects.get(id=responsible_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    'responsible_id': f"Usuario no encontrado: {responsible_id}"
                })
        
        return data


class ExportFormatSerializer(serializers.Serializer):
    """
    Serializer for export format information.
    """
    format = serializers.CharField(help_text="Nombre del formato")
    content_type = serializers.CharField(help_text="Tipo de contenido MIME")
    extension = serializers.CharField(help_text="Extensión de archivo")
    available = serializers.BooleanField(help_text="Si el formato está disponible")
    description = serializers.CharField(
        required=False,
        help_text="Descripción del formato"
    )