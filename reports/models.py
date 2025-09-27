from django.db import models
from django.conf import settings
from core.models import BaseModel


class ReportType(BaseModel):
    """
    Model to define different types of reports available in the system.
    """
    REPORT_TYPE_CHOICES = [
        ('pollination', 'Reporte de Polinización'),
        ('germination', 'Reporte de Germinación'),
        ('statistical', 'Reporte Estadístico'),
    ]
    
    name = models.CharField(
        max_length=50,
        choices=REPORT_TYPE_CHOICES,
        unique=True,
        help_text="Tipo de reporte"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Nombre para mostrar del tipo de reporte"
    )
    description = models.TextField(
        blank=True,
        help_text="Descripción detallada del tipo de reporte"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el tipo de reporte está activo"
    )
    template_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre del template para generar el reporte"
    )
    
    class Meta:
        verbose_name = "Tipo de Reporte"
        verbose_name_plural = "Tipos de Reporte"
        ordering = ['name']
    
    def __str__(self):
        return self.display_name
    
    def get_default_template(self):
        """
        Returns the default template name for this report type.
        """
        template_mapping = {
            'pollination': 'reports/pollination_report.html',
            'germination': 'reports/germination_report.html',
            'statistical': 'reports/statistical_report.html',
        }
        return template_mapping.get(self.name, 'reports/default_report.html')
    
    def save(self, *args, **kwargs):
        """
        Override save to set default template if not provided.
        """
        if not self.template_name:
            self.template_name = self.get_default_template()
        super().save(*args, **kwargs)


class Report(BaseModel):
    """
    Model to store generated reports with metadata.
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('generating', 'Generando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]
    
    title = models.CharField(
        max_length=200,
        help_text="Título del reporte"
    )
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.CASCADE,
        related_name='reports',
        help_text="Tipo de reporte"
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generated_reports',
        help_text="Usuario que generó el reporte"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Estado del reporte"
    )
    format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        default='pdf',
        help_text="Formato del reporte"
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parámetros utilizados para generar el reporte"
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Ruta del archivo generado"
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Tamaño del archivo en bytes"
    )
    generation_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de inicio de generación"
    )
    generation_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de finalización de generación"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Mensaje de error si la generación falló"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadatos adicionales del reporte"
    )
    
    class Meta:
        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['generated_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def get_file_name(self):
        """
        Returns the file name for the report.
        """
        if self.file_path:
            return self.file_path.split('/')[-1]
        return f"{self.title}_{self.created_at.strftime('%Y%m%d_%H%M%S')}.{self.format}"
    
    def get_generation_duration(self):
        """
        Returns the duration of report generation in seconds.
        """
        if self.generation_started_at and self.generation_completed_at:
            delta = self.generation_completed_at - self.generation_started_at
            return delta.total_seconds()
        return None
    
    def is_completed(self):
        """
        Returns True if the report generation is completed successfully.
        """
        return self.status == 'completed'
    
    def is_failed(self):
        """
        Returns True if the report generation failed.
        """
        return self.status == 'failed'
    
    def mark_as_generating(self):
        """
        Mark the report as currently being generated.
        """
        from django.utils import timezone
        self.status = 'generating'
        self.generation_started_at = timezone.now()
        self.save(update_fields=['status', 'generation_started_at'])
    
    def mark_as_completed(self, file_path=None, file_size=None):
        """
        Mark the report as completed successfully.
        """
        from django.utils import timezone
        self.status = 'completed'
        self.generation_completed_at = timezone.now()
        if file_path:
            self.file_path = file_path
        if file_size:
            self.file_size = file_size
        self.save(update_fields=['status', 'generation_completed_at', 'file_path', 'file_size'])
    
    def mark_as_failed(self, error_message=None):
        """
        Mark the report as failed with optional error message.
        """
        from django.utils import timezone
        self.status = 'failed'
        self.generation_completed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'generation_completed_at', 'error_message'])
