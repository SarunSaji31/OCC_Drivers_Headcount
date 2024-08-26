from django.contrib import admin
from .models import DriverTrip, DriverImportLog, DutyCardTrip

@admin.register(DriverTrip)
class DriverTripAdmin(admin.ModelAdmin):
    list_display = ['route_name', 'date', 'head_count', 'trip_type']

@admin.register(DriverImportLog)
class DriverImportLogAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'driver_name']

@admin.register(DutyCardTrip)
class DutyCardTripAdmin(admin.ModelAdmin):
    list_display = ['duty_card_no', 'route_name', 'shift_time']
    