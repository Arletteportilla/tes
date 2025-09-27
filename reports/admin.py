from django.contrib import admin
from django.utils.html import format_html
from .models import ReportType, Report


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    """
    Admin configuration for ReportType model.
    """
    list_display = ['name', 'display_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'name', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'display_name', 'description', 'is_active')
        }),
        ('Configuración', {
            'fields': ('template_name',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    Admin configuration for Report model.
    """
    list_display = [
        'title', 
        'report_type', 
        'generated_by', 
        'status_badge', 
        'format', 
        'file_size_display',
        'created_at'
    ]
    list_filter = [
        'status', 
        'format', 
        'report_type', 
        'created_at',
        'generation_completed_at'
    ]
    search_fields = ['title', 'generated_by__username', 'generated_by__email']
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'generation_started_at',
        'generation_completed_at',
        'file_size_display',
        'generation_duration_display'
    ]
    
    fieldsets = (
        ('Información del Reporte', {
            'fields': ('title', 'report_type', 'generated_by', 'status', 'format')
        }),
        ('Archivos y Resultados', {
            'fields': ('file_path', 'file_size_display', 'error_message')
        }),
        ('Parámetros', {
            'fields': ('parameters', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Tiempos de Generación', {
            'fields': (
                'generation_started_at', 
                'generation_completed_at',
                'generation_duration_display'
            ),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """
        Display status with colored badge.
        """
        colors = {
            'pending': 'orange',
            'generating': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def file_size_display(self, obj):
        """
        Display file size in human readable format.
        """
        if not obj.file_size:
            return '-'
        
        # Convert bytes to human readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if obj.file_size < 1024.0:
                return f"{obj.file_size:.1f} {unit}"
            obj.file_size /= 1024.0
        return f"{obj.file_size:.1f} TB"
    file_size_display.short_description = 'Tamaño del Archivo'
    
    def generation_duration_display(self, obj):
        """
        Display generation duration in human readable format.
        """
        duration = obj.get_generation_duration()
        if duration is None:
            return '-'
        
        if duration < 60:
            return f"{duration:.1f} segundos"
        elif duration < 3600:
            minutes = duration / 60
            return f"{minutes:.1f} minutos"
        else:
            hours = duration / 3600
            return f"{hours:.1f} horas"
    generation_duration_display.short_description = 'Duración de Generación'
    
    def get_queryset(self, request):
        """
        Optimize queryset with select_related.
        """
        return super().get_queryset(request).select_related(
            'report_type', 'generated_by'
        )
