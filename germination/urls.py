"""
URL configuration for the germination module.
Defines API endpoints for germination management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'germination'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'records', views.GerminationRecordViewSet, basename='germinationrecord')
router.register(r'seed-sources', views.SeedSourceViewSet, basename='seedsource')
router.register(r'setups', views.GerminationSetupViewSet, basename='germinationsetup')

urlpatterns = [
    path('', include(router.urls)),
]