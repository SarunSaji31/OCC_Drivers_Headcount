from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),  # Home view for the root URL
    path('enter_head_count/', views.enter_head_count, name='enter_head_count'),
    path('success/', views.success, name='success'),
    path('driver-autocomplete/', views.get_driver_name, name='driver-autocomplete'),  # Corrected function
    path('staff-id-autocomplete/', views.staff_id_autocomplete, name='staff-id-autocomplete'),
    path('get-driver-name/', views.get_driver_name, name='get-driver-name'),
    path('duty-card-no-autocomplete/', views.duty_card_no_autocomplete, name='duty-card-no-autocomplete'),
    path('get-duty-card-details/', views.get_duty_card_details, name='get-duty-card-details'),
    path('report/', views.report_view, name='report'),  # Add this line for the report view
    path('download_report/', views.download_report, name='download-report'),  # Add this line for downloading the report
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
