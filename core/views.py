"""
Core views for system information and testing.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


@extend_schema(
    tags=['System'],
    summary="Estado del sistema de testing",
    description="""
    Obtiene información sobre el estado actual del sistema de testing de APIs.
    
    Este endpoint está siempre disponible sin autenticación para verificar
    el estado de configuración del servidor.
    """,
    responses={
        200: OpenApiResponse(
            description="Estado del sistema",
            examples=[
                OpenApiExample(
                    'Modo de testing público',
                    value={
                        "debug_mode": True,
                        "public_api_testing": True,
                        "authentication_required": False,
                        "message": "APIs públicas habilitadas para testing",
                        "warning": "Este modo NO debe usarse en producción"
                    }
                ),
                OpenApiExample(
                    'Modo de producción',
                    value={
                        "debug_mode": False,
                        "public_api_testing": False,
                        "authentication_required": True,
                        "message": "Autenticación requerida para todos los endpoints protegidos"
                    }
                ),
            ]
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_testing_status(request):
    """
    Get current API testing configuration status.
    This endpoint is always public to check server configuration.
    """
    debug_mode = settings.DEBUG
    public_testing = getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False)
    
    response_data = {
        'debug_mode': debug_mode,
        'public_api_testing': public_testing,
        'authentication_required': not (debug_mode and public_testing),
        'server_time': request.META.get('HTTP_DATE'),
        'version': '1.0.0'
    }
    
    if debug_mode and public_testing:
        response_data.update({
            'message': 'APIs públicas habilitadas para testing',
            'warning': 'Este modo NO debe usarse en producción',
            'protected_endpoints': [
                '/api/auth/login/',
                '/api/auth/token/',
                '/api/auth/token/refresh/',
            ],
            'public_endpoints_info': 'Todos los demás endpoints están disponibles sin autenticación'
        })
    elif debug_mode:
        response_data.update({
            'message': 'Modo de desarrollo con autenticación habilitada',
            'info': 'Use los endpoints de login para obtener tokens JWT'
        })
    else:
        response_data.update({
            'message': 'Autenticación requerida para todos los endpoints protegidos',
            'info': 'Sistema en modo de producción'
        })
    
    return Response(response_data)


@extend_schema(
    tags=['System'],
    summary="Información del sistema",
    description="Obtiene información general del sistema y configuración",
    responses={
        200: OpenApiResponse(
            description="Información del sistema",
            examples=[
                OpenApiExample(
                    'Información del sistema',
                    value={
                        "system_name": "Sistema de Polinización y Germinación",
                        "version": "1.0.0",
                        "api_version": "v1",
                        "documentation_url": "/api/docs/",
                        "available_endpoints": {
                            "authentication": "/api/auth/",
                            "pollination": "/api/pollination/",
                            "germination": "/api/germination/",
                            "alerts": "/api/alerts/",
                            "reports": "/api/reports/"
                        }
                    }
                )
            ]
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def system_info(request):
    """
    Get general system information.
    This endpoint is always public.
    """
    return Response({
        'system_name': 'Sistema de Polinización y Germinación',
        'version': '1.0.0',
        'api_version': 'v1',
        'documentation_url': '/api/docs/',
        'redoc_url': '/api/redoc/',
        'schema_url': '/api/schema/',
        'available_endpoints': {
            'authentication': '/api/auth/',
            'pollination': '/api/pollination/',
            'germination': '/api/germination/',
            'alerts': '/api/alerts/',
            'reports': '/api/reports/',
            'system': '/api/system/'
        },
        'features': [
            'JWT Authentication',
            'Role-based permissions',
            'Pollination management',
            'Germination tracking',
            'Automated alerts',
            'Report generation',
            'API documentation'
        ]
    })