"""API Urls"""

from django.urls import include, path

urlpatterns = [
    path('', include('api.auth.views')),
    path('', include('api.doctors.views')),
    path('', include('api.patients.views')),
    path('', include('api.appointments.views')),
]
