"""
Views for the reports app.
Provides API endpoints for report generation and management.
"""

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
import os
import tempfile
from typing import Dict, Any
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample, OpenApiParameter

from .models import Report, ReportType
from .serializers import ReportSerializer, ReportTypeSerializer, ReportGenerationSerializer
from .services import ReportGeneratorService
from .export_services import ExportService
from .statistics_services import StatisticsService
from core.models import PermissionMixin


@extend_schema_view(
    list=extend_schema(
        tags=['Reports'],
        summary="Listar tipos de reporte",
        description="""
        Obtiene la lista de tipos de reporte disponibles en el sistema.
        
        Solo los administradores pueden acceder a esta funcionalidad.
        """,
        responses={
            200: OpenApiResponse(description="Lista de tipos de reporte disponibles"),
            403: OpenApiResponse(description="Permisos insuficientes - Solo administradores"),
        }
    ),
    retrieve=extend_schema(
        tags=['Reports'],
        summary="Obtener tipo de reporte específico",
        description="Obtiene los detalles de un tipo de reporte específico"
    ),
)
class ReportTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ReportType model.
    Provides read-only access to available report types.
    """
    queryset = ReportType.objects.filter(is_active=True)
    serializer_class = ReportTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'is_active']
    
    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Only administrators can see all report types.
        """
        queryset = super().get_queryset()
        
        # Only administrators can access reports
        if not PermissionMixin.can_generate_reports(self.request.user):
            return queryset.none()
        
        return queryset


@extend_schema_view(
    list=extend_schema(
        tags=['Reports'],
        summary="Listar reportes generados",
        description="""
        Obtiene la lista de reportes generados por el usuario.
        
        Los administradores pueden ver todos los reportes, otros usuarios solo los propios.
        """,
        parameters=[
            OpenApiParameter(
                name='status',
                description='Filtrar por estado del reporte',
                required=False,
                type=str,
                enum=['pending', 'generating', 'completed', 'failed']
            ),
            OpenApiParameter(
                name='format',
                description='Filtrar por formato del reporte',
                required=False,
                type=str,
                enum=['pdf', 'excel']
            ),
            OpenApiParameter(
                name='report_type',
                description='Filtrar por tipo de reporte (ID)',
                required=False,
                type=int
            ),
        ]
    ),
    create=extend_schema(
        tags=['Reports'],
        summary="Crear nuevo reporte",
        description="Crea un nuevo registro de reporte (usar generate_report para generar contenido)"
    ),
    retrieve=extend_schema(
        tags=['Reports'],
        summary="Obtener reporte específico",
        description="Obtiene los detalles de un reporte específico"
    ),
    update=extend_schema(
        tags=['Reports'],
        summary="Actualizar reporte",
        description="Actualiza los metadatos de un reporte existente"
    ),
    destroy=extend_schema(
        tags=['Reports'],
        summary="Eliminar reporte",
        description="Elimina un reporte y sus archivos asociados"
    ),
)
class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Report model.
    Provides CRUD operations and report generation functionality.
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'format', 'report_type', 'generated_by']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Users can only see their own reports unless they're administrators.
        """
        queryset = super().get_queryset()
        
        # Only administrators can generate reports
        if not PermissionMixin.can_generate_reports(self.request.user):
            return queryset.none()
        
        # Administrators can see all reports, others only their own
        if not self.request.user.is_superuser:
            queryset = queryset.filter(generated_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Set the generated_by field to the current user.
        """
        serializer.save(generated_by=self.request.user)
    
    @extend_schema(
        tags=['Reports'],
        summary="Generar nuevo reporte",
        description="""
        Genera un nuevo reporte basado en los parámetros proporcionados.
        
        El proceso incluye:
        1. Validación de parámetros
        2. Generación de datos del reporte
        3. Exportación al formato solicitado
        4. Almacenamiento del archivo generado
        """,
        request=ReportGenerationSerializer,
        examples=[
            OpenApiExample(
                'Reporte de polinización',
                value={
                    "report_type": "pollination",
                    "title": "Reporte Mensual de Polinización",
                    "format": "pdf",
                    "parameters": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-31",
                        "responsible_id": 1
                    }
                },
                request_only=True,
            ),
            OpenApiExample(
                'Reporte de germinación',
                value={
                    "report_type": "germination",
                    "title": "Estadísticas de Germinación Q1",
                    "format": "excel",
                    "parameters": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-03-31",
                        "plant_genus": "Orchidaceae"
                    }
                },
                request_only=True,
            ),
        ],
        responses={
            201: OpenApiResponse(
                description="Reporte generado exitosamente",
                examples=[
                    OpenApiExample(
                        'Reporte generado',
                        value={
                            "id": 15,
                            "title": "Reporte Mensual de Polinización",
                            "status": "completed",
                            "format": "pdf",
                            "file_path": "/media/reports/pollination_report_2024_01.pdf",
                            "generated_at": "2024-01-31T10:30:00Z",
                            "download_url": "/api/reports/15/download/"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="Parámetros inválidos"),
            403: OpenApiResponse(description="Permisos insuficientes"),
        }
    )
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_report(self, request):
        """
        Generate a new report based on provided parameters.
        """
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para generar reportes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReportGenerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        try:
            with transaction.atomic():
                # Get report type
                report_type = ReportType.objects.get(
                    name=validated_data['report_type'],
                    is_active=True
                )
                
                # Create report record
                report = Report.objects.create(
                    title=validated_data['title'],
                    report_type=report_type,
                    generated_by=request.user,
                    format=validated_data['format'],
                    parameters=validated_data['parameters'],
                    status='generating'
                )
                
                # Mark as generating
                report.mark_as_generating()
                
                try:
                    # Generate report data
                    generator_service = ReportGeneratorService()
                    report_data = generator_service.generate_report(report)
                    
                    # Export report
                    export_service = ExportService()
                    exported_content = export_service.export_report(
                        report_data,
                        validated_data['format'],
                        validated_data['title']
                    )
                    
                    # Save to temporary file (in production, you'd save to proper storage)
                    file_extension = export_service.get_file_extension(validated_data['format'])
                    filename = f"report_{report.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
                    
                    # Create reports directory if it doesn't exist
                    reports_dir = os.path.join('media', 'reports')
                    os.makedirs(reports_dir, exist_ok=True)
                    
                    file_path = os.path.join(reports_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(exported_content)
                    
                    # Mark as completed
                    report.mark_as_completed(
                        file_path=file_path,
                        file_size=len(exported_content)
                    )
                    
                    # Update metadata
                    report.metadata = {
                        'generation_method': 'api',
                        'export_format': validated_data['format'],
                        'data_summary': report_data.get('metadata', {}),
                        'file_info': {
                            'filename': filename,
                            'size_bytes': len(exported_content)
                        }
                    }
                    report.save()
                    
                except Exception as e:
                    # Mark as failed
                    report.mark_as_failed(str(e))
                    raise
                
                # Return report info
                response_serializer = ReportSerializer(report)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except ReportType.DoesNotExist:
            return Response(
                {'error': f'Tipo de reporte no encontrado: {validated_data["report_type"]}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error generando reporte: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='download')
    def download_report(self, request, pk=None):
        """
        Download a generated report file.
        """
        report = self.get_object()
        
        # Check if report is completed and has a file
        if not report.is_completed() or not report.file_path:
            return Response(
                {'error': 'El reporte no está disponible para descarga'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if file exists
        if not os.path.exists(report.file_path):
            return Response(
                {'error': 'El archivo del reporte no se encuentra'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Read file content
            with open(report.file_path, 'rb') as f:
                file_content = f.read()
            
            # Get content type
            export_service = ExportService()
            content_type = export_service.get_content_type(report.format)
            
            # Create response
            response = HttpResponse(file_content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{report.get_file_name()}"'
            response['Content-Length'] = len(file_content)
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error descargando reporte: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='regenerate')
    def regenerate_report(self, request, pk=None):
        """
        Regenerate an existing report with the same parameters.
        """
        original_report = self.get_object()
        
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para generar reportes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            with transaction.atomic():
                # Create new report with same parameters
                new_report = Report.objects.create(
                    title=f"{original_report.title} (Regenerado)",
                    report_type=original_report.report_type,
                    generated_by=request.user,
                    format=original_report.format,
                    parameters=original_report.parameters,
                    status='generating'
                )
                
                # Mark as generating
                new_report.mark_as_generating()
                
                try:
                    # Generate report data
                    generator_service = ReportGeneratorService()
                    report_data = generator_service.generate_report(new_report)
                    
                    # Export report
                    export_service = ExportService()
                    exported_content = export_service.export_report(
                        report_data,
                        new_report.format,
                        new_report.title
                    )
                    
                    # Save file
                    file_extension = export_service.get_file_extension(new_report.format)
                    filename = f"report_{new_report.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
                    
                    reports_dir = os.path.join('media', 'reports')
                    os.makedirs(reports_dir, exist_ok=True)
                    file_path = os.path.join(reports_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(exported_content)
                    
                    # Mark as completed
                    new_report.mark_as_completed(
                        file_path=file_path,
                        file_size=len(exported_content)
                    )
                    
                    # Update metadata
                    new_report.metadata = {
                        'generation_method': 'regeneration',
                        'original_report_id': original_report.id,
                        'export_format': new_report.format,
                        'data_summary': report_data.get('metadata', {}),
                        'file_info': {
                            'filename': filename,
                            'size_bytes': len(exported_content)
                        }
                    }
                    new_report.save()
                    
                except Exception as e:
                    # Mark as failed
                    new_report.mark_as_failed(str(e))
                    raise
                
                # Return new report info
                response_serializer = ReportSerializer(new_report)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Error regenerando reporte: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='available-formats')
    def available_formats(self, request):
        """
        Get list of available export formats.
        """
        export_service = ExportService()
        formats = export_service.get_available_formats()
        
        format_info = []
        for fmt in formats:
            format_info.append({
                'format': fmt,
                'content_type': export_service.get_content_type(fmt),
                'extension': export_service.get_file_extension(fmt)
            })
        
        return Response({
            'available_formats': format_info
        })


class StatisticsViewSet(viewsets.GenericViewSet):
    """
    ViewSet for statistics functionality.
    Provides endpoints for statistical analysis of pollination and germination data.
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statistics_service = StatisticsService()
    
    @action(detail=False, methods=['get'], url_path='comprehensive')
    def comprehensive_statistics(self, request):
        """
        Get comprehensive statistics combining pollination and germination data.
        
        Query parameters:
        - start_date: Start date for analysis (YYYY-MM-DD)
        - end_date: End date for analysis (YYYY-MM-DD)
        - responsible_id: Filter by specific user ID
        - pollination_type: Filter by pollination type
        - genus: Filter by plant genus
        """
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para acceder a estadísticas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Parse query parameters
            parameters = {
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'responsible_id': request.query_params.get('responsible_id'),
                'pollination_type': request.query_params.get('pollination_type'),
                'genus': request.query_params.get('genus'),
            }
            
            # Remove None values
            parameters = {k: v for k, v in parameters.items() if v is not None}
            
            # Get comprehensive statistics
            statistics = self.statistics_service.get_comprehensive_statistics(parameters)
            
            return Response(statistics)
            
        except Exception as e:
            return Response(
                {'error': f'Error generando estadísticas: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='pollination')
    def pollination_statistics(self, request):
        """
        Get detailed pollination statistics.
        
        Query parameters:
        - start_date: Start date for analysis (YYYY-MM-DD)
        - end_date: End date for analysis (YYYY-MM-DD)
        - responsible_id: Filter by specific user ID
        - pollination_type: Filter by pollination type
        - genus: Filter by plant genus
        """
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para acceder a estadísticas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Parse query parameters
            parameters = {
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'responsible_id': request.query_params.get('responsible_id'),
                'pollination_type': request.query_params.get('pollination_type'),
                'genus': request.query_params.get('genus'),
            }
            
            # Remove None values
            parameters = {k: v for k, v in parameters.items() if v is not None}
            
            # Get pollination statistics
            statistics = self.statistics_service.pollination_stats.get_statistics(parameters)
            
            return Response({
                'pollination_statistics': statistics,
                'metadata': {
                    'generated_at': timezone.now().isoformat(),
                    'filters_applied': parameters
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error generando estadísticas de polinización: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='germination')
    def germination_statistics(self, request):
        """
        Get detailed germination statistics.
        
        Query parameters:
        - start_date: Start date for analysis (YYYY-MM-DD)
        - end_date: End date for analysis (YYYY-MM-DD)
        - responsible_id: Filter by specific user ID
        - genus: Filter by plant genus
        """
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para acceder a estadísticas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Parse query parameters
            parameters = {
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'responsible_id': request.query_params.get('responsible_id'),
                'genus': request.query_params.get('genus'),
            }
            
            # Remove None values
            parameters = {k: v for k, v in parameters.items() if v is not None}
            
            # Get germination statistics
            statistics = self.statistics_service.germination_stats.get_statistics(parameters)
            
            return Response({
                'germination_statistics': statistics,
                'metadata': {
                    'generated_at': timezone.now().isoformat(),
                    'filters_applied': parameters
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error generando estadísticas de germinación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='summary')
    def summary_statistics(self, request):
        """
        Get high-level summary statistics for dashboard display.
        
        Query parameters:
        - start_date: Start date for analysis (YYYY-MM-DD)
        - end_date: End date for analysis (YYYY-MM-DD)
        """
        # Check permissions - allow all authenticated users to see summary
        try:
            # Parse query parameters
            parameters = {
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
            }
            
            # Remove None values
            parameters = {k: v for k, v in parameters.items() if v is not None}
            
            # Get comprehensive statistics but return only summary
            full_statistics = self.statistics_service.get_comprehensive_statistics(parameters)
            
            # Extract summary information
            summary = {
                'summary': full_statistics['summary'],
                'recent_trends': {
                    'monthly_trends': full_statistics['trends']['monthly_trends'][-3:],  # Last 3 months
                    'growth_rates': full_statistics['trends']['growth_rates']
                },
                'top_performers': {
                    'users': full_statistics['performance']['user_performance'][:5],  # Top 5 users
                    'species': full_statistics['performance']['species_performance'][:5]  # Top 5 species
                },
                'metadata': full_statistics['metadata']
            }
            
            return Response(summary)
            
        except Exception as e:
            return Response(
                {'error': f'Error generando resumen estadístico: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='performance')
    def performance_statistics(self, request):
        """
        Get performance and efficiency statistics.
        
        Query parameters:
        - start_date: Start date for analysis (YYYY-MM-DD)
        - end_date: End date for analysis (YYYY-MM-DD)
        - user_id: Filter by specific user ID
        """
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para acceder a estadísticas de rendimiento'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Parse query parameters
            parameters = {
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'user_id': request.query_params.get('user_id'),
            }
            
            # Remove None values
            parameters = {k: v for k, v in parameters.items() if v is not None}
            
            # Get comprehensive statistics and extract performance data
            full_statistics = self.statistics_service.get_comprehensive_statistics(parameters)
            
            performance_data = {
                'user_performance': full_statistics['performance']['user_performance'],
                'species_performance': full_statistics['performance']['species_performance'],
                'success_rates': full_statistics['performance']['success_rates'],
                'productivity_metrics': full_statistics['performance']['productivity_metrics'],
                'comparative_analysis': full_statistics['comparative'],
                'metadata': full_statistics['metadata']
            }
            
            return Response(performance_data)
            
        except Exception as e:
            return Response(
                {'error': f'Error generando estadísticas de rendimiento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='trends')
    def trend_statistics(self, request):
        """
        Get trend analysis over time.
        
        Query parameters:
        - start_date: Start date for analysis (YYYY-MM-DD)
        - end_date: End date for analysis (YYYY-MM-DD)
        """
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para acceder a análisis de tendencias'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Parse query parameters
            parameters = {
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
            }
            
            # Remove None values
            parameters = {k: v for k, v in parameters.items() if v is not None}
            
            # Get comprehensive statistics and extract trend data
            full_statistics = self.statistics_service.get_comprehensive_statistics(parameters)
            
            trend_data = {
                'trends': full_statistics['trends'],
                'temporal_patterns': {
                    'pollination': full_statistics['pollination']['temporal_distribution'],
                    'germination': full_statistics['germination']['temporal_distribution']
                },
                'metadata': full_statistics['metadata']
            }
            
            return Response(trend_data)
            
        except Exception as e:
            return Response(
                {'error': f'Error generando análisis de tendencias: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExportView(viewsets.GenericViewSet):
    """
    ViewSet for direct export functionality.
    Provides endpoints for immediate report export without saving to database.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='export-direct')
    def export_direct(self, request):
        """
        Generate and export a report directly without saving to database.
        Useful for quick exports or previews.
        """
        # Check permissions
        if not PermissionMixin.can_generate_reports(request.user):
            return Response(
                {'error': 'No tiene permisos para generar reportes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReportGenerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        try:
            # Get report type
            report_type = ReportType.objects.get(
                name=validated_data['report_type'],
                is_active=True
            )
            
            # Create temporary report object for generation
            temp_report = Report(
                title=validated_data['title'],
                report_type=report_type,
                generated_by=request.user,
                format=validated_data['format'],
                parameters=validated_data['parameters']
            )
            
            # Generate report data
            generator_service = ReportGeneratorService()
            report_data = generator_service.generate_report(temp_report)
            
            # Export report
            export_service = ExportService()
            exported_content = export_service.export_report(
                report_data,
                validated_data['format'],
                validated_data['title']
            )
            
            # Return as download
            content_type = export_service.get_content_type(validated_data['format'])
            file_extension = export_service.get_file_extension(validated_data['format'])
            filename = f"{validated_data['title'].replace(' ', '_')}{file_extension}"
            
            response = HttpResponse(exported_content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(exported_content)
            
            return response
            
        except ReportType.DoesNotExist:
            return Response(
                {'error': f'Tipo de reporte no encontrado: {validated_data["report_type"]}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error exportando reporte: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
