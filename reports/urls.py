"""
URL configuration for reports app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, ReportTypeViewSet, ExportView, StatisticsViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'report-types', ReportTypeViewSet, basename='reporttype')
router.register(r'export', ExportView, basename='export')
router.register(r'statistics', StatisticsViewSet, basename='statistics')

app_name = 'reports'

urlpatterns = [
    path('api/', include(router.urls)),
]