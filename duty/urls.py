from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),  # Home view for the root URL
    path('enter_head_count/', views.enter_head_count, name='enter_head_count'),  # URL for entering head count
    path('success/', views.success, name='success'),  # URL for the success page after form submission

    # Autocomplete endpoints
    path('driver-autocomplete/', views.get_driver_name, name='driver-autocomplete'),  # Autocomplete for driver names
    path('staff-id-autocomplete/', views.staff_id_autocomplete, name='staff-id-autocomplete'),  # Autocomplete for staff IDs
    path('duty-card-no-autocomplete/', views.duty_card_no_autocomplete, name='duty-card-no-autocomplete'),  # Autocomplete for duty card numbers
    path('route-autocomplete/', views.route_autocomplete, name='route-autocomplete'),  # Autocomplete for route names
    path('shift-time-autocomplete/', views.shift_time_autocomplete, name='shift-time-autocomplete'),  # Autocomplete for shift times

    # Data retrieval endpoints
    path('get-driver-name/', views.get_driver_name, name='get-driver-name'),  # Get driver name based on staff ID
    path('get-duty-card-details/', views.get_duty_card_details, name='get-duty-card-details'),  # Get details based on duty card number

    # Report and download endpoints
    path('report/', views.report_view, name='report'),  # View to display the report
    path('download_report/', views.download_report, name='download_report'),  # View to download the report as XLSX

    # Authentication URLs
    path('accounts/', include('django.contrib.auth.urls')),  # Includes login, logout, password reset, etc.

    # Sign up endpoint
    path('signup/', views.signup, name='signup'),  # Sign up page for new users
    
    # Logout endpoint
    path('logout/', views.user_logout, name='logout'),  # Custom logout view
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
