from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from .models import Role, UserProfile
from .serializers import (
    CustomTokenObtainPairSerializer,
    LoginSerializer,
    TokenRefreshSerializer,
    UserSerializer,
    RoleSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    UserRegistrationSerializer
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view that includes user information.
    """
    serializer_class = CustomTokenObtainPairSerializer
    
    @extend_schema(
        tags=['Authentication'],
        summary="Obtener token JWT",
        description="""
        Autentica al usuario con credenciales (username/password) y devuelve tokens JWT.
        
        El token de acceso tiene una duración limitada y debe incluirse en el header Authorization
        para acceder a endpoints protegidos. El token de actualización permite obtener nuevos
        tokens de acceso sin reautenticarse.
        """,
        examples=[
            OpenApiExample(
                'Ejemplo de login',
                value={
                    'username': 'usuario@ejemplo.com',
                    'password': 'contraseña123'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta exitosa',
                value={
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'user': {
                        'id': 1,
                        'username': 'usuario@ejemplo.com',
                        'email': 'usuario@ejemplo.com',
                        'first_name': 'Juan',
                        'last_name': 'Pérez',
                        'role': 'Polinizador'
                    }
                },
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Autenticación exitosa - Devuelve tokens JWT y datos del usuario"
            ),
            401: OpenApiResponse(
                description="Credenciales inválidas - Usuario o contraseña incorrectos"
            ),
            400: OpenApiResponse(
                description="Datos de entrada inválidos - Campos requeridos faltantes"
            ),
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LoginView(APIView):
    """
    Alternative login view using custom serializer.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Authentication'],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login exitoso - Devuelve tokens JWT y datos del usuario"
            ),
            400: OpenApiResponse(
                description="Credenciales inválidas o datos de entrada incorrectos"
            ),
        },
        summary="Login alternativo de usuario",
        description="""
        Endpoint alternativo para autenticación de usuarios usando serializer personalizado.
        
        Funcionalidad idéntica al endpoint estándar de JWT pero con validaciones adicionales
        y respuesta personalizada que incluye información extendida del usuario.
        """,
        examples=[
            OpenApiExample(
                'Login exitoso',
                value={
                    'username': 'germinador@ejemplo.com',
                    'password': 'password123'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta de login',
                value={
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'user': {
                        'id': 2,
                        'username': 'germinador@ejemplo.com',
                        'email': 'germinador@ejemplo.com',
                        'first_name': 'María',
                        'last_name': 'González',
                        'role': 'Germinador',
                        'employee_id': 'EMP002'
                    }
                },
                response_only=True,
            ),
        ]
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            
            # Add custom claims
            access['username'] = user.username
            access['email'] = user.email
            access['role'] = user.get_role_name() if user.role else None
            access['employee_id'] = user.employee_id
            
            return Response({
                'access': str(access),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view that includes user information.
    """
    serializer_class = TokenRefreshSerializer
    
    @extend_schema(
        summary="Renovar token JWT",
        description="Renueva el token de acceso usando el token de actualización",
        responses={
            200: OpenApiResponse(description="Token renovado exitosamente"),
            401: OpenApiResponse(description="Token de actualización inválido"),
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """
    Logout view that blacklists the refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Cerrar sesión",
        description="Cierra la sesión del usuario y blacklistea el token de actualización",
        responses={
            200: OpenApiResponse(description="Sesión cerrada exitosamente"),
            400: OpenApiResponse(description="Token inválido"),
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response(
                    {"message": "Sesión cerrada exitosamente"}, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Token de actualización requerido"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except TokenError as e:
            return Response(
                {"error": "Token inválido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Error al cerrar sesión"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    View for user profile management.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        summary="Obtener perfil de usuario",
        description="Obtiene la información del perfil del usuario autenticado"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Actualizar perfil de usuario",
        description="Actualiza la información del perfil del usuario autenticado"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class PasswordChangeView(APIView):
    """
    View for changing user password.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description="Contraseña cambiada exitosamente"),
            400: OpenApiResponse(description="Datos inválidos"),
        },
        summary="Cambiar contraseña",
        description="Cambia la contraseña del usuario autenticado"
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Contraseña cambiada exitosamente"}, 
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationView(generics.CreateAPIView):
    """
    View for user registration (admin only).
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Only administrators can create users
        if not self.request.user.has_role('Administrador') and not self.request.user.is_superuser:
            raise PermissionDenied("Solo los administradores pueden crear usuarios.")
        serializer.save()
    
    @extend_schema(
        summary="Registrar nuevo usuario",
        description="Registra un nuevo usuario en el sistema (solo administradores)",
        responses={
            201: OpenApiResponse(description="Usuario creado exitosamente"),
            403: OpenApiResponse(description="Permisos insuficientes"),
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RoleListView(generics.ListAPIView):
    """
    View for listing available roles.
    """
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Listar roles disponibles",
        description="Obtiene la lista de roles disponibles en el sistema"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(
    summary="Verificar estado de autenticación",
    description="Verifica si el usuario está autenticado y devuelve información básica",
    responses={
        200: OpenApiResponse(description="Usuario autenticado"),
        401: OpenApiResponse(description="Usuario no autenticado"),
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def auth_status(request):
    """
    Check authentication status and return user info.
    """
    user_data = UserSerializer(request.user).data
    return Response({
        'authenticated': True,
        'user': user_data
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Verificar permisos de usuario",
    description="Verifica los permisos del usuario para diferentes módulos",
    responses={
        200: OpenApiResponse(description="Información de permisos"),
        401: OpenApiResponse(description="Usuario no autenticado"),
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_permissions(request):
    """
    Get user permissions for different modules.
    """
    user = request.user
    modules = ['pollination', 'germination', 'alerts', 'reports', 'authentication']
    
    permissions_data = {
        'role': user.get_role_name(),
        'modules': {
            module: user.has_module_permission(module) 
            for module in modules
        },
        'can_delete_records': user.can_delete_records(),
        'can_generate_reports': user.can_generate_reports(),
        'is_superuser': user.is_superuser
    }
    
    return Response(permissions_data, status=status.HTTP_200_OK)
