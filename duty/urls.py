from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import (
    add_reports,
    add_delay_report,
    stm_dashboard,
    fleet_counts_api,
    download_fleet_report,
    get_most_delayed_trips_api,
)

urlpatterns = [
    # Root URL (home page)
    path('', views.home, name='home'),

    # Enter head count URL
    path('enter_head_count/', views.enter_head_count, name='enter_head_count'),

    # Success page after form submission
    path('success/', views.success, name='success'),

    # Autocomplete endpoints for dynamic form fields
    path('driver-autocomplete/', views.get_driver_name, name='driver-autocomplete'),
    path('staff-id-autocomplete/', views.staff_id_autocomplete, name='staff-id-autocomplete'),
    path('duty-card-no-autocomplete/', views.duty_card_no_autocomplete, name='duty-card-no-autocomplete'),
    path('route-autocomplete/', views.route_autocomplete, name='route-autocomplete'),
    path('shift-time-autocomplete/', views.shift_time_autocomplete, name='shift-time-autocomplete'),

    # Data retrieval endpoints for forms
    path('get-driver-name/', views.get_driver_name, name='get-driver-name'),
    path('get-duty-card-details/', views.get_duty_card_details, name='get-duty-card-details'),

    # Report viewing and downloading
    path('report/', views.report_view, name='report'),
    path('download_report/', views.download_report, name='download_report'),

    # Authentication-related URLs (login, logout, password management)
    path('accounts/', include('django.contrib.auth.urls')),

    # User sign-up URL
    path('signup/', views.signup, name='signup'),

    # Custom logout view
    path('logout/', views.user_logout, name='logout'),

    # Custom password reset views without email
    path('password_reset/', views.password_reset_request, name='password_reset'),
    path('set_new_password/<int:user_id>/', views.set_new_password, name='set_new_password'),

    # Dashboard URLs
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('dashboard/data/', views.dashboard_data, name='dashboard_data'),
    path('dashboard/duty-card-submission-data/', views.duty_card_submission_data, name='duty_card_submission_data'),

    # EKG Report and Delay Report
    path('ekg-report/', add_reports, name='ekg_report'),
    path('add_delay_report/', add_delay_report, name='add_delay_report'),

    # Subcategory Selection Page
    path('subcategory/', views.subcategory_selection, name='subcategory_selection'),

    # EKG Breakdown Page
    path('ekg-breakdown/', views.ekg_breakdown, name='ekg_breakdown'),

    # STM Dashboard
    path('stm-dashboard/', stm_dashboard, name='stm_dashboard'),
    path('api/fleet-counts/', fleet_counts_api, name='fleet_counts_api'),
    path('download_fleet_report/', download_fleet_report, name='download_fleet_report'),

    # Search and Route Details URLs
    path('search/', views.ajax_search_route, name='search_route'),
    path('ajax/search_route/', views.ajax_search_route, name='ajax_search_route'),
    path('route-details/', views.route_details, name='route_details'),
    path('stm_timetables/', views.stm_timetables, name='stm_timetable'),

    # Upload and download
    path('upload/', views.upload_view, name='upload'),
    path('download/<str:filename>/', views.download_file, name='download_file'),

    # Most Delayed Trips API
    path('get-most-delayed-trips-api/', get_most_delayed_trips_api, name='get_most_delayed_trips_api'),
    # submission history
    path('submission-history/', views.submission_history, name='submission_history'),   
    path('user_submission_history/', views.submission_history, name='user_submission_history'),  
    path('filter-dashboard/', views.filter_dashboard, name='filter_dashboard'), 
    path('public-stm-dashboard/', views.public_stm_dashboard, name='public_stm_dashboard'),
    path('get-otp-chart-data/', views.get_otp_chart_data, name='get_otp_chart_data'),

]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
