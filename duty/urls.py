from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('enter_head_count/', views.enter_head_count, name='enter_head_count'),
    path('success/', views.success, name='success'),
    path('driver-autocomplete/', views.driver_autocomplete, name='driver-autocomplete'),
    path('staff-id-autocomplete/', views.staff_id_autocomplete, name='staff-id-autocomplete'),
    path('get-driver-name/', views.get_driver_name, name='get-driver-name'),
]
