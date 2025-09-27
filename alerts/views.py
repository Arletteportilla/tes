from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample, OpenApiParameter

from alerts.models import Alert, AlertType, UserAlert
from alerts.serializers import (
    AlertSerializer, AlertTypeSerializer, UserAlertSerializer,
    NotificationSummarySerializer, MarkNotificationActionSerializer,
    BulkNotificationActionSerializer
)
from alerts.services import NotificationService
from core.models import PermissionMixin


class AlertTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AlertType model.
    Provides read-only access to alert types.
    """
    queryset = AlertType.objects.filter(is_active=True)
    serializer_class = AlertTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['name', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Alert model.
    Provides read-only access to alerts with filtering and actions.
    """
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['status', 'priority', 'alert_type__name']
    search_fields = ['title', 'message']
    ordering_fields = ['scheduled_date', 'created_at', 'priority']
    ordering = ['-scheduled_date', '-created_at']
    
    def get_queryset(self):
        """
        Filter alerts based on user permissions.
        Users can only see alerts assigned to them.
        """
        user = self.request.user
        
        # Administrators can see all alerts
        if PermissionMixin.has_role_permission(user, 'Administrador'):
            return Alert.objects.all().select_related('alert_type')
        
        # Regular users can only see their own alerts
        return Alert.objects.filter(
            user_alerts__user=user
        ).select_related('alert_type').distinct()
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a specific alert as read for the current user"""
        alert = self.get_object()
        success = NotificationService.mark_notification_as_read(request.user, alert.id)
        
        if success:
            return Response({'message': 'Alert marked as read'})
        else:
            return Response(
                {'error': 'Alert not found or not assigned to user'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def mark_as_dismissed(self, request, pk=None):
        """Mark a specific alert as dismissed for the current user"""
        alert = self.get_object()
        success = NotificationService.mark_notification_as_dismissed(request.user, alert.id)
        
        if success:
            return Response({'message': 'Alert marked as dismissed'})
        else:
            return Response(
                {'error': 'Alert not found or not assigned to user'}, 
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema_view(
    list=extend_schema(
        tags=['Alerts'],
        summary="Listar notificaciones del usuario",
        description="""
        Obtiene todas las notificaciones del usuario autenticado.
        
        Las notificaciones incluyen alertas de polinización, germinación y otras
        actividades del sistema relevantes para el usuario.
        """,
        parameters=[
            OpenApiParameter(
                name='is_read',
                description='Filtrar por estado de lectura',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='is_dismissed',
                description='Filtrar por estado de descarte',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='alert__priority',
                description='Filtrar por prioridad (low, medium, high)',
                required=False,
                type=str,
                enum=['low', 'medium', 'high']
            ),
        ]
    ),
    retrieve=extend_schema(
        tags=['Alerts'],
        summary="Obtener notificación específica",
        description="Obtiene los detalles de una notificación específica del usuario"
    ),
)
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notifications (UserAlert model).
    Provides comprehensive notification management for users.
    """
    serializer_class = UserAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read', 'is_dismissed', 'alert__priority', 'alert__alert_type__name']
    ordering_fields = ['alert__scheduled_date', 'created_at', 'alert__priority']
    ordering = ['-alert__scheduled_date', '-created_at']
    
    def get_queryset(self):
        """
        Return notifications for the current user only.
        """
        return NotificationService.get_user_notifications(self.request.user)
    
    @extend_schema(
        tags=['Alerts'],
        summary="Resumen de notificaciones",
        description="Obtiene un resumen de las notificaciones del usuario con contadores por estado",
        responses={
            200: OpenApiResponse(
                description="Resumen de notificaciones",
                examples=[
                    OpenApiExample(
                        'Resumen ejemplo',
                        value={
                            "total_notifications": 15,
                            "unread_count": 5,
                            "dismissed_count": 3,
                            "by_priority": {
                                "high": 2,
                                "medium": 8,
                                "low": 5
                            },
                            "by_type": {
                                "semanal": 6,
                                "preventiva": 4,
                                "frecuente": 5
                            }
                        }
                    )
                ]
            )
        }
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get notification summary for the current user"""
        summary = NotificationService.get_notification_summary(request.user)
        serializer = NotificationSummarySerializer(summary)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Alerts'],
        summary="Notificaciones no leídas",
        description="Obtiene solo las notificaciones no leídas del usuario",
        parameters=[
            OpenApiParameter(
                name='limit',
                description='Límite de notificaciones a devolver',
                required=False,
                type=int
            ),
        ],
        responses={
            200: OpenApiResponse(description="Lista de notificaciones no leídas")
        }
    )
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get only unread notifications for the current user"""
        limit = request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                limit = None
        
        notifications = NotificationService.get_user_notifications(
            request.user, 
            limit=limit, 
            unread_only=True
        )
        
        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get notifications filtered by alert type"""
        alert_type = request.query_params.get('type')
        if not alert_type:
            return Response(
                {'error': 'Alert type parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notifications = NotificationService.get_notifications_by_type(
            request.user, 
            alert_type
        )
        
        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_priority(self, request):
        """Get notifications filtered by priority"""
        priority = request.query_params.get('priority')
        if not priority:
            return Response(
                {'error': 'Priority parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notifications = NotificationService.get_notifications_by_priority(
            request.user, 
            priority
        )
        
        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a specific notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_dismissed(self, request, pk=None):
        """Mark a specific notification as dismissed"""
        notification = self.get_object()
        notification.mark_as_dismissed()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for the current user"""
        count = NotificationService.mark_all_notifications_as_read(request.user)
        return Response({
            'message': f'Marked {count} notifications as read'
        })
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on notifications"""
        serializer = BulkNotificationActionSerializer(data=request.data)
        if serializer.is_valid():
            action_type = serializer.validated_data['action']
            alert_type = serializer.validated_data.get('alert_type')
            priority = serializer.validated_data.get('priority')
            
            if action_type == 'mark_all_read':
                # Filter notifications based on criteria
                queryset = UserAlert.objects.filter(
                    user=request.user,
                    is_read=False
                )
                
                if alert_type:
                    queryset = queryset.filter(alert__alert_type__name=alert_type)
                
                if priority:
                    queryset = queryset.filter(alert__priority=priority)
                
                # Mark as read
                count = 0
                for notification in queryset:
                    notification.mark_as_read()
                    count += 1
                
                return Response({
                    'message': f'Marked {count} notifications as read'
                })
            
            elif action_type == 'dismiss_all_read':
                # Dismiss all read notifications
                queryset = UserAlert.objects.filter(
                    user=request.user,
                    is_read=True,
                    is_dismissed=False
                )
                
                if alert_type:
                    queryset = queryset.filter(alert__alert_type__name=alert_type)
                
                if priority:
                    queryset = queryset.filter(alert__priority=priority)
                
                count = 0
                for notification in queryset:
                    notification.mark_as_dismissed()
                    count += 1
                
                return Response({
                    'message': f'Dismissed {count} read notifications'
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def cleanup_old(self, request):
        """Clean up old notifications for the current user"""
        days_old = request.data.get('days_old', 30)
        try:
            days_old = int(days_old)
        except (ValueError, TypeError):
            days_old = 30
        
        count = NotificationService.cleanup_old_notifications(request.user, days_old)
        return Response({
            'message': f'Cleaned up {count} old notifications'
        })