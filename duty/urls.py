from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

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

    path('dashboard/', views.admin_dashboard, name='dashboard'),  # For rendering the page
    path('dashboard/data/', views.dashboard_data, name='dashboard_data'),
    path('dashboard/duty-card-submission-data/', views.duty_card_submission_data, name='duty_card_submission_data'), 
    
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
