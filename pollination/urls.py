"""
URLs for pollination app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlantViewSet, PollinationTypeViewSet, 
    ClimateConditionViewSet, PollinationRecordViewSet
)

app_name = 'pollination'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'plants', PlantViewSet, basename='plant')
router.register(r'pollination-types', PollinationTypeViewSet, basename='pollinationtype')
router.register(r'climate-conditions', ClimateConditionViewSet, basename='climatecondition')
router.register(r'records', PollinationRecordViewSet, basename='pollinationrecord')

urlpatterns = [
    path('', include(router.urls)),
]