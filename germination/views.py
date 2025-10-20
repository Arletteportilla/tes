"""
Views for the germination module.
Provides REST API endpoints for germination management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from datetime import date, timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample, OpenApiParameter

from .models import GerminationRecord, SeedSource, GerminationSetup
from .serializers import (
    GerminationRecordSerializer, GerminationRecordCreateSerializer,
    GerminationRecordUpdateSerializer, SeedSourceSerializer,
    GerminationSetupSerializer, GerminationStatisticsSerializer,
    TransplantRecommendationSerializer, SeedSourceListSerializer,
    GerminationSetupListSerializer
)
from .services import GerminationService, GerminationValidationService
from authentication.permissions import RoleBasedPermission


@extend_schema_view(
    list=extend_schema(
        tags=['Germination'],
        summary="Listar registros de germinación",
        description="""
        Obtiene la lista de registros de germinación con filtros opcionales.
        
        Los usuarios no administradores solo pueden ver sus propios registros.
        """,
        parameters=[
            OpenApiParameter(
                name='responsible',
                description='Filtrar por usuario responsable (ID)',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='plant__genus',
                description='Filtrar por género de la planta',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='plant__species',
                description='Filtrar por especie de la planta',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='transplant_confirmed',
                description='Filtrar por estado de confirmación de trasplante',
                required=False,
                type=bool
            ),
        ]
    ),
    create=extend_schema(
        tags=['Germination'],
        summary="Crear registro de germinación",
        description="""
        Crea un nuevo registro de germinación.
        
        El sistema calculará automáticamente la fecha estimada de trasplante
        basada en la especie de la planta y las condiciones de germinación.
        """,
        examples=[
            OpenApiExample(
                'Registro de germinación',
                value={
                    "germination_date": "2024-01-20",
                    "plant": 1,
                    "seed_source": 1,
                    "germination_condition": 1,
                    "seeds_planted": 50,
                    "seedlings_germinated": 42,
                    "observations": "Germinación exitosa en condiciones controladas"
                },
                request_only=True,
            ),
        ]
    ),
    retrieve=extend_schema(
        tags=['Germination'],
        summary="Obtener registro específico",
        description="Obtiene los detalles completos de un registro de germinación"
    ),
    update=extend_schema(
        tags=['Germination'],
        summary="Actualizar registro completo",
        description="Actualiza completamente un registro de germinación existente"
    ),
    partial_update=extend_schema(
        tags=['Germination'],
        summary="Actualizar registro parcialmente",
        description="Actualiza parcialmente un registro de germinación existente"
    ),
    destroy=extend_schema(
        tags=['Germination'],
        summary="Eliminar registro",
        description="Elimina un registro de germinación (solo administradores)"
    ),
)
class GerminationRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing germination records.
    Provides CRUD operations and additional business logic endpoints.
    """
    queryset = GerminationRecord.objects.select_related(
        'responsible', 'plant', 'seed_source', 'germination_condition'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'responsible', 'plant__genus', 'plant__species', 'seed_source__source_type',
        'germination_condition__climate', 'is_successful', 'transplant_confirmed'
    ]
    search_fields = [
        'plant__genus', 'plant__species', 'seed_source__name',
        'observations', 'germination_condition__location'
    ]
    ordering_fields = [
        'germination_date', 'estimated_transplant_date', 'created_at',
        'seeds_planted', 'seedlings_germinated'
    ]
    ordering = ['-germination_date', '-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return GerminationRecordCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return GerminationRecordUpdateSerializer
        return GerminationRecordSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Non-admin users can only see their own records
        if not user.is_staff and hasattr(user, 'role'):
            if user.role.name in ['Germinador', 'Polinizador']:
                queryset = queryset.filter(responsible=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the responsible user when creating a record."""
        serializer.save(responsible=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Only allow admin users to delete records."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Solo los administradores pueden eliminar registros'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    @extend_schema(
        tags=['Germination'],
        summary="Estadísticas de germinación",
        description="""
        Obtiene estadísticas detalladas de los procesos de germinación.
        
        Incluye tasas de germinación, éxito de trasplantes y análisis por períodos.
        Los administradores pueden ver estadísticas globales.
        """,
        parameters=[
            OpenApiParameter(
                name='start_date',
                description='Fecha de inicio para el rango de estadísticas (YYYY-MM-DD)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='end_date',
                description='Fecha de fin para el rango de estadísticas (YYYY-MM-DD)',
                required=False,
                type=str
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Estadísticas de germinación",
                examples=[
                    OpenApiExample(
                        'Estadísticas ejemplo',
                        value={
                            "total_records": 25,
                            "total_seeds_planted": 1250,
                            "total_seedlings_germinated": 1050,
                            "average_germination_rate": 84.0,
                            "transplant_success_rate": 92.5,
                            "by_genus": {
                                "Orchidaceae": {
                                    "records": 15,
                                    "germination_rate": 88.0
                                }
                            }
                        }
                    )
                ]
            )
        }
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get germination statistics for the current user or all users (admin).
        """
        queryset = self.get_queryset()
        
        # Apply date filters if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(germination_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(germination_date__lte=end_date)
        
        # Calculate statistics
        records = list(queryset)
        stats = GerminationService.calculate_germination_statistics(records)
        
        # Add date range to response
        if start_date:
            stats['period_start'] = start_date
        if end_date:
            stats['period_end'] = end_date
        
        serializer = GerminationStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Germination'],
        summary="Trasplantes pendientes",
        description="""
        Obtiene los registros de germinación que tienen trasplantes pendientes.
        
        Incluye recomendaciones específicas para cada trasplante basadas en
        las condiciones actuales y el estado de las plántulas.
        """,
        parameters=[
            OpenApiParameter(
                name='days_ahead',
                description='Días hacia adelante para considerar trasplantes pendientes (por defecto 30)',
                required=False,
                type=int
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Lista de trasplantes pendientes con recomendaciones",
                examples=[
                    OpenApiExample(
                        'Trasplantes pendientes',
                        value=[
                            {
                                "germination_record_id": 5,
                                "plant_name": "Orchidaceae Cattleya",
                                "germination_date": "2024-01-20",
                                "estimated_transplant_date": "2024-02-20",
                                "days_remaining": 5,
                                "recommendations": {
                                    "optimal_conditions": "Temperatura 20-25°C, humedad 70%",
                                    "substrate": "Mezcla de corteza y musgo",
                                    "care_notes": "Riego moderado, evitar encharcamiento"
                                }
                            }
                        ]
                    )
                ]
            )
        }
    )
    @action(detail=False, methods=['get'])
    def pending_transplants(self, request):
        """
        Get germination records with pending transplants.
        """
        days_ahead = int(request.query_params.get('days_ahead', 30))
        user = request.user if not request.user.is_staff else None
        
        pending_records = GerminationService.get_pending_transplants(
            user=user, days_ahead=days_ahead
        )
        
        recommendations = []
        for record in pending_records:
            recommendation_data = GerminationService.get_transplant_recommendations(record)
            recommendations.append({
                'germination_record_id': record.id,
                'plant_name': str(record.plant),
                'germination_date': record.germination_date,
                'estimated_transplant_date': record.estimated_transplant_date,
                'days_remaining': record.days_to_transplant(),
                **recommendation_data
            })
        
        serializer = TransplantRecommendationSerializer(recommendations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue_transplants(self, request):
        """
        Get germination records with overdue transplants.
        """
        user = request.user if not request.user.is_staff else None
        
        overdue_records = GerminationService.get_overdue_transplants(user=user)
        
        recommendations = []
        for record in overdue_records:
            recommendation_data = GerminationService.get_transplant_recommendations(record)
            recommendations.append({
                'germination_record_id': record.id,
                'plant_name': str(record.plant),
                'germination_date': record.germination_date,
                'estimated_transplant_date': record.estimated_transplant_date,
                'days_remaining': record.days_to_transplant(),
                **recommendation_data
            })
        
        serializer = TransplantRecommendationSerializer(recommendations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def confirm_transplant(self, request, pk=None):
        """
        Confirm transplant for a germination record.
        """
        record = self.get_object()
        
        if record.transplant_confirmed:
            return Response(
                {'error': 'El trasplante ya ha sido confirmado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        confirmed_date = request.data.get('confirmed_date', date.today())
        is_successful = request.data.get('is_successful', True)
        
        try:
            record.confirm_transplant(confirmed_date, is_successful)
            serializer = self.get_serializer(record)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def by_genus(self, request):
        """
        Get germination records grouped by plant genus.
        """
        queryset = self.get_queryset()
        
        genus_stats = queryset.values('plant__genus').annotate(
            total_records=Count('id'),
            total_seeds=Count('seeds_planted'),
            total_germinated=Count('seedlings_germinated'),
            avg_germination_rate=Avg('seedlings_germinated')
        ).order_by('plant__genus')
        
        return Response(genus_stats)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent germination records (last 30 days).
        """
        thirty_days_ago = date.today() - timedelta(days=30)
        queryset = self.get_queryset().filter(germination_date__gte=thirty_days_ago)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SeedSourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing seed sources.
    Provides CRUD operations for seed source management.
    """
    queryset = SeedSource.objects.select_related('pollination_record').all()
    serializer_class = SeedSourceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source_type', 'is_active', 'pollination_record']
    search_fields = ['name', 'description', 'external_supplier']
    ordering_fields = ['name', 'source_type', 'collection_date', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SeedSourceListSerializer
        return SeedSourceSerializer
    
    def get_queryset(self):
        """Filter queryset to show only active sources by default."""
        queryset = super().get_queryset()
        
        # Show only active sources unless specifically requested
        show_inactive = self.request.query_params.get('show_inactive', 'false').lower() == 'true'
        if not show_inactive:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Get seed sources grouped by source type.
        """
        queryset = self.get_queryset()
        
        type_stats = queryset.values('source_type').annotate(
            count=Count('id')
        ).order_by('source_type')
        
        return Response(type_stats)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate a seed source.
        """
        source = self.get_object()
        source.is_active = False
        source.save()
        
        serializer = self.get_serializer(source)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate a seed source.
        """
        source = self.get_object()
        source.is_active = True
        source.save()
        
        serializer = self.get_serializer(source)
        return Response(serializer.data)


class GerminationSetupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing germination setups.
    Provides CRUD operations for germination configurations.
    """
    queryset = GerminationSetup.objects.all()
    serializer_class = GerminationSetupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['climate', 'substrate']
    search_fields = ['location', 'substrate_details', 'notes']
    ordering_fields = ['climate', 'substrate', 'location', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return GerminationSetupListSerializer
        return GerminationSetupSerializer
    
    @action(detail=False, methods=['get'])
    def by_climate(self, request):
        """
        Get germination conditions grouped by climate type.
        """
        queryset = self.get_queryset()
        
        climate_stats = queryset.values('climate').annotate(
            count=Count('id')
        ).order_by('climate')
        
        return Response(climate_stats)
    
    @action(detail=False, methods=['get'])
    def by_substrate(self, request):
        """
        Get germination conditions grouped by substrate type.
        """
        queryset = self.get_queryset()
        
        substrate_stats = queryset.values('substrate').annotate(
            count=Count('id')
        ).order_by('substrate')
        
        return Response(substrate_stats)
