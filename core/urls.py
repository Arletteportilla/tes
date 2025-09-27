"""
URLs for the core app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('testing-status/', views.api_testing_status, name='api-testing-status'),
    path('info/', views.system_info, name='system-info'),
]