from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import add_reports, add_delay_report, send_breakdown_report_email
from .views import stm_dashboard, fleet_counts_api, download_fleet_report

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
    path('send-breakdown-report/', send_breakdown_report_email, name='send_breakdown_report'),

    # STM Dashboard
    path('stm-dashboard/', stm_dashboard, name='stm_dashboard'),
    path('api/fleet-counts/', fleet_counts_api, name='fleet_counts_api'),
    path('download_fleet_report/', download_fleet_report, name='download_fleet_report'),

    # Search and Route Details URLs
    path('search/', views.ajax_search_route, name='search_route'),
    path('ajax/search_route/', views.ajax_search_route, name='ajax_search_route'),
    path('route-details/', views.route_details, name='route_details'),  # New route details page
    path('stm_timetables/', views.stm_timetables, name='stm_timetable'), 
    path('submission-history/', views.submission_history, name='submission_history'),
    path('user_submission_history/', views.submission_history, name='user_submission_history'),
     
    path('category/', views.category_page, name='category_page'),

    path('shift_duty/', views.shift_duty_page, name='shift_duty'),
    path('duty_schedule/', views.duty_schedule_page, name='duty_schedule'),
    path('handle_trip/', views.handle_trip, name='handle_trip'),



    
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)