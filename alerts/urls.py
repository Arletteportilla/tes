"""
URLs for alerts app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from alerts.views import AlertTypeViewSet, AlertViewSet, NotificationViewSet

app_name = 'alerts'

router = DefaultRouter()
router.register(r'alert-types', AlertTypeViewSet, basename='alerttype')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]