from django.contrib import admin
from .models import DriverImportLog, DriverTrip, DutyCardTrip

# Register DriverImportLog model
@admin.register(DriverImportLog)
class DriverImportLogAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'driver_name')  # Customize the columns you want to display in the admin panel
    search_fields = ('staff_id', 'driver_name')  # Add search functionality

# Register DriverTrip model
@admin.register(DriverTrip)
class DriverTripAdmin(admin.ModelAdmin):
    list_display = ('route_name', 'shift_time', 'trip_type', 'date', 'head_count')
    search_fields = ('route_name', 'trip_type')
    list_filter = ('shift_time', 'trip_type', 'date')  # Add filters for easy navigation

# Register DutyCardTrip model
@admin.register(DutyCardTrip)
class DutyCardTripAdmin(admin.ModelAdmin):
    list_display = ('duty_card_no', 'route_name', 'trip_type', 'pick_up_time', 'drop_off_time', 'shift_time')
    search_fields = ('duty_card_no', 'route_name')