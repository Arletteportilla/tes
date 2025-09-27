from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from datetime import date, timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample, OpenApiParameter

from .models import Plant, PollinationType, ClimateCondition, PollinationRecord
from .serializers import (
    PlantSerializer, PollinationTypeSerializer, ClimateConditionSerializer,
    PollinationRecordSerializer, PollinationRecordCreateSerializer,
    PollinationRecordUpdateSerializer, MaturationConfirmationSerializer,
    PollinationStatisticsSerializer, PlantCompatibilitySerializer
)
from .services import PollinationService, ValidationService
from authentication.permissions import RoleBasedPermission


@extend_schema_view(
    list=extend_schema(
        tags=['Plants'],
        summary="Listar plantas",
        description="Obtiene la lista de plantas disponibles en el sistema con filtros opcionales",
        parameters=[
            OpenApiParameter(
                name='genus',
                description='Filtrar por género de la planta',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='species',
                description='Filtrar por especie de la planta',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='vivero',
                description='Filtrar por vivero donde se encuentra la planta',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='include_inactive',
                description='Incluir plantas inactivas (por defecto solo activas)',
                required=False,
                type=bool
            ),
        ]
    ),
    create=extend_schema(
        tags=['Plants'],
        summary="Crear nueva planta",
        description="Registra una nueva planta en el catálogo del sistema"
    ),
    retrieve=extend_schema(
        tags=['Plants'],
        summary="Obtener planta específica",
        description="Obtiene los detalles de una planta específica por su ID"
    ),
    update=extend_schema(
        tags=['Plants'],
        summary="Actualizar planta",
        description="Actualiza completamente los datos de una planta existente"
    ),
    partial_update=extend_schema(
        tags=['Plants'],
        summary="Actualizar planta parcialmente",
        description="Actualiza parcialmente los datos de una planta existente"
    ),
    destroy=extend_schema(
        tags=['Plants'],
        summary="Eliminar planta",
        description="Elimina una planta del catálogo (solo administradores)"
    ),
)
class PlantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing plants.
    Provides CRUD operations for plant records.
    """
    queryset = Plant.objects.all()
    serializer_class = PlantSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['genus', 'species', 'vivero', 'is_active']
    search_fields = ['genus', 'species', 'vivero', 'mesa', 'pared']
    ordering_fields = ['genus', 'species', 'vivero', 'created_at']
    ordering = ['genus', 'species', 'vivero', 'mesa', 'pared']
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        
        # Filter by active plants by default
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @extend_schema(
        tags=['Plants'],
        summary="Plantas agrupadas por especie",
        description="Obtiene las plantas organizadas por especie (género + especie)",
        responses={
            200: OpenApiResponse(
                description="Plantas agrupadas por especie",
                examples=[
                    OpenApiExample(
                        'Ejemplo de respuesta',
                        value={
                            "Orchidaceae Cattleya": [
                                {
                                    "id": 1,
                                    "genus": "Orchidaceae",
                                    "species": "Cattleya",
                                    "vivero": "Vivero A",
                                    "mesa": "Mesa 1",
                                    "pared": "Norte"
                                }
                            ]
                        }
                    )
                ]
            )
        }
    )
    @action(detail=False, methods=['get'])
    def by_species(self, request):
        """Get plants grouped by species."""
        queryset = self.get_queryset()
        species_data = {}
        
        for plant in queryset:
            species_key = f"{plant.genus} {plant.species}"
            if species_key not in species_data:
                species_data[species_key] = []
            species_data[species_key].append(PlantSerializer(plant).data)
        
        return Response(species_data)
    
    @extend_schema(
        tags=['Plants'],
        summary="Ubicaciones disponibles",
        description="Obtiene la lista de viveros únicos donde se encuentran las plantas",
        responses={
            200: OpenApiResponse(
                description="Lista de ubicaciones (viveros)",
                examples=[
                    OpenApiExample(
                        'Ubicaciones',
                        value=["Vivero A", "Vivero B", "Invernadero 1"]
                    )
                ]
            )
        }
    )
    @action(detail=False, methods=['get'])
    def locations(self, request):
        """Get unique locations (viveros)."""
        locations = self.get_queryset().values_list('vivero', flat=True).distinct()
        return Response(list(locations))


class PollinationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for pollination types.
    Read-only access to pollination type definitions.
    """
    queryset = PollinationType.objects.all()
    serializer_class = PollinationTypeSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def validate_compatibility(self, request, pk=None):
        """Validate plant compatibility for this pollination type."""
        pollination_type = self.get_object()
        
        try:
            mother_plant_id = request.data.get('mother_plant_id')
            father_plant_id = request.data.get('father_plant_id')
            
            if not mother_plant_id:
                return Response(
                    {'error': 'mother_plant_id es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            mother_plant = Plant.objects.get(id=mother_plant_id)
            father_plant = None
            if father_plant_id:
                father_plant = Plant.objects.get(id=father_plant_id)
            
            compatibility = ValidationService.validate_plant_compatibility(
                mother_plant, father_plant, pollination_type
            )
            
            return Response({
                'is_compatible': compatibility['is_compatible'],
                'errors': compatibility['errors'],
                'pollination_type': PollinationTypeSerializer(pollination_type).data
            })
            
        except Plant.DoesNotExist:
            return Response(
                {'error': 'Una o más plantas no existen'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ClimateConditionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing climate conditions.
    Provides CRUD operations for climate condition records.
    """
    queryset = ClimateCondition.objects.all()
    serializer_class = ClimateConditionSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['weather']
    ordering_fields = ['weather', 'temperature', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent climate conditions (last 30 days)."""
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_conditions = self.get_queryset().filter(
            created_at__date__gte=thirty_days_ago
        )
        serializer = self.get_serializer(recent_conditions, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=['Pollination'],
        summary="Listar registros de polinización",
        description="""
        Obtiene la lista de registros de polinización con filtros y búsqueda.
        
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
                name='pollination_type',
                description='Filtrar por tipo de polinización (ID)',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='maturation_confirmed',
                description='Filtrar por estado de confirmación de maduración',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='maturation_status',
                description='Filtrar por estado de maduración (pending, approaching, overdue, confirmed)',
                required=False,
                type=str,
                enum=['pending', 'approaching', 'overdue', 'confirmed']
            ),
        ]
    ),
    create=extend_schema(
        tags=['Pollination'],
        summary="Crear registro de polinización",
        description="""
        Crea un nuevo registro de polinización.
        
        El sistema validará automáticamente:
        - Compatibilidad de plantas según el tipo de polinización
        - Fechas válidas (no futuras)
        - Datos requeridos según el tipo seleccionado
        """,
        examples=[
            OpenApiExample(
                'Polinización Self',
                value={
                    "pollination_type": 1,
                    "pollination_date": "2024-01-15",
                    "mother_plant": 1,
                    "new_plant": 2,
                    "climate_condition": 1,
                    "capsules_quantity": 5,
                    "observations": "Polinización realizada en condiciones óptimas"
                },
                request_only=True,
            ),
            OpenApiExample(
                'Polinización Híbrido',
                value={
                    "pollination_type": 3,
                    "pollination_date": "2024-01-15",
                    "mother_plant": 1,
                    "father_plant": 3,
                    "new_plant": 4,
                    "climate_condition": 1,
                    "capsules_quantity": 3,
                    "observations": "Cruce entre especies diferentes"
                },
                request_only=True,
            ),
        ]
    ),
    retrieve=extend_schema(
        tags=['Pollination'],
        summary="Obtener registro específico",
        description="Obtiene los detalles completos de un registro de polinización"
    ),
    update=extend_schema(
        tags=['Pollination'],
        summary="Actualizar registro completo",
        description="Actualiza completamente un registro de polinización existente"
    ),
    partial_update=extend_schema(
        tags=['Pollination'],
        summary="Actualizar registro parcialmente",
        description="Actualiza parcialmente un registro de polinización existente"
    ),
    destroy=extend_schema(
        tags=['Pollination'],
        summary="Eliminar registro",
        description="Elimina un registro de polinización (solo administradores)"
    ),
)
class PollinationRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing pollination records.
    Provides full CRUD operations with specialized actions.
    """
    queryset = PollinationRecord.objects.select_related(
        'responsible', 'pollination_type', 'mother_plant',
        'father_plant', 'new_plant', 'climate_condition'
    ).all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'responsible', 'pollination_type', 'maturation_confirmed',
        'is_successful', 'pollination_date'
    ]
    search_fields = [
        'mother_plant__genus', 'mother_plant__species',
        'father_plant__genus', 'father_plant__species',
        'observations'
    ]
    ordering_fields = ['pollination_date', 'created_at', 'estimated_maturation_date']
    ordering = ['-pollination_date', '-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return PollinationRecordCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PollinationRecordUpdateSerializer
        return PollinationRecordSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters."""
        queryset = super().get_queryset()
        
        # Filter by current user if not admin
        user = self.request.user
        if not user.has_role('Administrador'):
            queryset = queryset.filter(responsible=user)
        
        # Filter by maturation status
        status_filter = self.request.query_params.get('maturation_status')
        if status_filter:
            queryset = PollinationService.get_records_by_maturation_status(
                user=user if not user.has_role('Administrador') else None,
                status_filter=status_filter
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the responsible user to current user."""
        serializer.save(responsible=self.request.user)
    
    @extend_schema(
        tags=['Pollination'],
        summary="Confirmar maduración",
        description="""
        Confirma la maduración de un registro de polinización.
        
        Permite registrar si el proceso fue exitoso y añadir observaciones adicionales.
        """,
        request=MaturationConfirmationSerializer,
        examples=[
            OpenApiExample(
                'Confirmación exitosa',
                value={
                    "confirmed_date": "2024-03-15",
                    "is_successful": True,
                    "notes": "Maduración completa, cápsulas desarrolladas correctamente"
                },
                request_only=True,
            ),
            OpenApiExample(
                'Confirmación fallida',
                value={
                    "confirmed_date": "2024-03-15",
                    "is_successful": False,
                    "notes": "No se observó desarrollo de cápsulas"
                },
                request_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Maduración confirmada exitosamente"),
            400: OpenApiResponse(description="Datos inválidos o registro ya confirmado"),
            404: OpenApiResponse(description="Registro no encontrado"),
        }
    )
    @action(detail=True, methods=['post'])
    def confirm_maturation(self, request, pk=None):
        """Confirm maturation of a pollination record."""
        record = self.get_object()
        serializer = MaturationConfirmationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                confirmed_record = PollinationService.confirm_maturation(
                    record,
                    confirmed_date=serializer.validated_data.get('confirmed_date'),
                    is_successful=serializer.validated_data.get('is_successful', True)
                )
                
                # Add notes to observations if provided
                notes = serializer.validated_data.get('notes')
                if notes:
                    if confirmed_record.observations:
                        confirmed_record.observations += f"\n\nConfirmación: {notes}"
                    else:
                        confirmed_record.observations = f"Confirmación: {notes}"
                    confirmed_record.save()
                
                return Response({
                    'message': 'Maduración confirmada exitosamente',
                    'record': PollinationRecordSerializer(confirmed_record).data
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=['Pollination'],
        summary="Estadísticas de polinización",
        description="""
        Obtiene estadísticas detalladas de los procesos de polinización.
        
        Los administradores pueden ver estadísticas globales, otros usuarios solo las propias.
        """,
        parameters=[
            OpenApiParameter(
                name='date_from',
                description='Fecha de inicio para el rango de estadísticas (YYYY-MM-DD)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='date_to',
                description='Fecha de fin para el rango de estadísticas (YYYY-MM-DD)',
                required=False,
                type=str
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Estadísticas de polinización",
                examples=[
                    OpenApiExample(
                        'Estadísticas ejemplo',
                        value={
                            "total_records": 45,
                            "confirmed_records": 38,
                            "success_rate": 84.4,
                            "by_type": {
                                "Self": {"count": 20, "success_rate": 90.0},
                                "Sibling": {"count": 15, "success_rate": 80.0},
                                "Híbrido": {"count": 10, "success_rate": 70.0}
                            },
                            "pending_confirmation": 7,
                            "overdue_confirmation": 2
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="Formato de fecha inválido"),
        }
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get pollination statistics."""
        user = request.user
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Parse dates if provided
        if date_from:
            try:
                date_from = date.fromisoformat(date_from)
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido para date_from'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if date_to:
            try:
                date_to = date.fromisoformat(date_to)
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido para date_to'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get statistics
        stats_user = None if user.has_role('Administrador') else user
        stats = PollinationService.get_success_statistics(
            user=stats_user,
            date_from=date_from,
            date_to=date_to
        )
        
        serializer = PollinationStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_maturation(self, request):
        """Get records pending maturation confirmation."""
        user = request.user
        records = PollinationService.get_records_by_maturation_status(
            user=user if not user.has_role('Administrador') else None,
            status_filter='approaching'
        )
        
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue records."""
        user = request.user
        records = PollinationService.get_records_by_maturation_status(
            user=user if not user.has_role('Administrador') else None,
            status_filter='overdue'
        )
        
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get records grouped by pollination type."""
        queryset = self.get_queryset()
        type_data = {}
        
        for record in queryset:
            type_name = record.pollination_type.name
            if type_name not in type_data:
                type_data[type_name] = []
            type_data[type_name].append(PollinationRecordSerializer(record).data)
        
        return Response(type_data)
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get dashboard summary data."""
        user = request.user
        user_filter = None if user.has_role('Administrador') else user
        
        # Get counts for different statuses
        pending = PollinationService.get_records_by_maturation_status(
            user=user_filter, status_filter='pending'
        ).count()
        
        approaching = PollinationService.get_records_by_maturation_status(
            user=user_filter, status_filter='approaching'
        ).count()
        
        overdue = PollinationService.get_records_by_maturation_status(
            user=user_filter, status_filter='overdue'
        ).count()
        
        confirmed = PollinationService.get_records_by_maturation_status(
            user=user_filter, status_filter='confirmed'
        ).count()
        
        # Get recent records (last 7 days)
        seven_days_ago = date.today() - timedelta(days=7)
        recent_queryset = self.get_queryset().filter(
            pollination_date__gte=seven_days_ago
        )
        recent_records = self.get_serializer(recent_queryset[:5], many=True).data
        
        return Response({
            'counts': {
                'pending': pending,
                'approaching': approaching,
                'overdue': overdue,
                'confirmed': confirmed,
                'total': pending + approaching + overdue + confirmed
            },
            'recent_records': recent_records,
            'alerts': {
                'approaching_maturation': approaching,
                'overdue_maturation': overdue
            }
        })
