from django.contrib import admin
from .models import DriverImportLog, DriverTrip, DutyCardTrip, DelayData, BreakdownReport,StmRoute, StmPickupPoint, StmShiftTime


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

# Register DelayData model
@admin.register(DelayData)
class DelayDataAdmin(admin.ModelAdmin):
    list_display = ('route', 'date', 'std', 'atd', 'sta', 'ata', 'delay')
    search_fields = ('route', 'date')
    list_filter = ('date', 'route')  # Add filters to navigate by route and date

# Register BreakdownReport model
@admin.register(BreakdownReport)
class BreakdownReportAdmin(admin.ModelAdmin):
    list_display = ('report_datetime', 'breakdown_datetime', 'route_number', 'location', 'driver_name', 'vehicle_make_plate', 'reported_to_person')
    search_fields = ('route_number', 'driver_name', 'vehicle_make_plate', 'reported_to_person')
    list_filter = ('breakdown_datetime', 'route_number')  # Filter by breakdown time and route number


from .models import StmRoute, StmPickupPoint, StmShiftTime
from django.contrib import admin

class StmShiftTimeInline(admin.TabularInline):
    model = StmShiftTime
    extra = 1
    fields = ('time', 'special_time', 'shift_time', 'stop_order')
    ordering = ['stop_order']

class StmPickupPointInline(admin.TabularInline):
    model = StmPickupPoint
    extra = 1
    fields = ('stop_id', 'pick_up_point', 'pick_up_point_order_id')  # Added 'pick_up_point_order_id'
    show_change_link = True
    ordering = ['pick_up_point_order_id']  # Order pickup points by the new field

@admin.register(StmRoute)
class StmRouteAdmin(admin.ModelAdmin):
    list_display = ['route_id', 'route', 'route_type', 'operating_days_1', 'work_hub']
    search_fields = ['route_id', 'route']
    inlines = [StmPickupPointInline, StmShiftTimeInline]

@admin.register(StmPickupPoint)
class StmPickupPointAdmin(admin.ModelAdmin):
    list_display = ['route', 'stop_id', 'pick_up_point', 'pick_up_point_order_id']  # Display 'pick_up_point_order_id'
    search_fields = ['route__route', 'stop_id']
    ordering = ['pick_up_point_order_id']  # Order by the new field

@admin.register(StmShiftTime)
class StmShiftTimeAdmin(admin.ModelAdmin):
    list_display = ['route', 'time', 'special_time', 'shift_time', 'stop_order']
    search_fields = ['route__route', 'shift_time']
