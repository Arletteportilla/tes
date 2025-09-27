"""
URLs for authentication app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenVerifyView
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    LoginView,
    LogoutView,
    UserProfileView,
    PasswordChangeView,
    UserRegistrationView,
    RoleListView,
    auth_status,
    user_permissions
)

app_name = 'authentication'

router = DefaultRouter()

urlpatterns = [
    # JWT Token endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Authentication endpoints
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # User management endpoints
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('register/', UserRegistrationView.as_view(), name='user_registration'),
    
    # Role and permissions endpoints
    path('roles/', RoleListView.as_view(), name='role_list'),
    path('status/', auth_status, name='auth_status'),
    path('permissions/', user_permissions, name='user_permissions'),
    
    # Router URLs
    path('', include(router.urls)),
]