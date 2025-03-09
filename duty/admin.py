from django.contrib import admin
from .models import (
    DriverImportLog, DriverTrip, DutyCardTrip, DelayData, BreakdownReport, 
    StmRoute, StmPickupPoint, StmShiftTime, BusKmTracking, BusMasterList
)

# Register DriverImportLog model
@admin.register(DriverImportLog)
class DriverImportLogAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'driver_name')
    search_fields = ('staff_id', 'driver_name')
    list_per_page = 20
    ordering = ('staff_id',)


# Register DutyCardTrip model
@admin.register(DutyCardTrip)
class DutyCardTripAdmin(admin.ModelAdmin):
    list_display = ('duty_card_no', 'route_name', 'trip_type', 'pick_up_time', 'drop_off_time', 'shift_time', 'capacity')
    search_fields = ('duty_card_no', 'route_name')
    list_filter = ('trip_type', 'shift_time')
    list_per_page = 20
    ordering = ('duty_card_no',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('duty_card_no', 'route_name', 'trip_type'),
            'description': 'Provide the basic details of the duty card.'
        }),
        ('Timing Details', {
            'fields': ('pick_up_time', 'drop_off_time', 'shift_time'),
            'description': 'Ensure the timing details match the route schedule.'
        }),
        ('Additional Details', {
            'fields': ('capacity', 'submission_date'),
            'description': 'Review capacity and submission date for record purposes.'
        }),
    )
    readonly_fields = ('submission_date',)


# Register DriverTrip model
@admin.register(DriverTrip)
class DriverTripAdmin(admin.ModelAdmin):
    list_display = ('route_name', 'shift_time', 'trip_type', 'duty_card', 'date', 'head_count')
    search_fields = ('route_name', 'trip_type', 'duty_card__duty_card_no')
    list_filter = ('duty_card', 'shift_time', 'trip_type', 'date')
    list_per_page = 200
    ordering = ('-date', 'route_name')

    fieldsets = (
        ('Trip Information', {
            'fields': ('driver', 'duty_card', 'route_name', 'trip_type'),
            'description': 'Specify the main details of the trip.'
        }),
        ('Timing Details', {
            'fields': ('pick_up_time', 'drop_off_time', 'shift_time'),
            'description': 'Ensure the timing details match the driver schedule.'
        }),
        ('Additional Details', {
            'fields': ('head_count', 'date'),
            'description': 'Provide additional details like head count and date.'
        }),
    )


# Register DelayData model
@admin.register(DelayData)
class DelayDataAdmin(admin.ModelAdmin):
    list_display = ('route', 'date', 'std', 'atd', 'sta', 'ata', 'delay')
    search_fields = ('route',)
    list_filter = ('date', 'route')
    ordering = ('-date', 'route')


# Register BreakdownReport model
@admin.register(BreakdownReport)
class BreakdownReportAdmin(admin.ModelAdmin):
    list_display = ('report_datetime', 'breakdown_datetime', 'route_number', 'location', 'driver_name', 'vehicle_make_plate', 'reported_to_person')
    search_fields = ('route_number', 'driver_name', 'vehicle_make_plate', 'reported_to_person')
    list_filter = ('breakdown_datetime', 'route_number')
    ordering = ('-breakdown_datetime',)


# Register BusKmTracking model
@admin.register(BusKmTracking)
class BusKmTrackingAdmin(admin.ModelAdmin):
    list_display = ('duty_card_no', 'bus_no', 'driver', 'submission_date', 'start_km', 'end_km', 'bus_change')
    search_fields = ('duty_card_no', 'bus_no', 'driver__driver_name')
    list_filter = ('submission_date', 'bus_change')
    list_per_page = 50
    ordering = ('-submission_date',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('duty_card', 'duty_card_no', 'driver', 'submission_date', 'bus_no'),
        }),
        ('Kilometer Details', {
            'fields': ('start_km', 'end_km', 'bus_change', 'changed_bus_no'),
        }),
        ('Time Details', {
            'fields': ('bus_start_time', 'bus_end_time', 'start_time', 'end_time'),
        }),
        ('Additional', {
            'fields': ('start_km_change', 'end_km_change'),
        }),
    )


# Inline Pickup Points for StmRoute
class StmPickupPointInline(admin.TabularInline):
    model = StmPickupPoint
    extra = 1
    fields = ['stop_id', 'pick_up_point', 'pick_up_point_order_id']
    ordering = ['pick_up_point_order_id']
    verbose_name = "Pickup Point"
    verbose_name_plural = "Pickup Points"


# Inline Shift Times for StmRoute
class StmShiftTimeInline(admin.TabularInline):
    model = StmShiftTime
    extra = 1
    fields = ['time', 'special_time', 'shift_time', 'stop_order']
    ordering = ['shift_time', 'stop_order']
    verbose_name = "Shift Time"
    verbose_name_plural = "Shift Times"


# Register StmRoute model
@admin.register(StmRoute)
class StmRouteAdmin(admin.ModelAdmin):
    list_display = ['route_id', 'route', 'route_type', 'operating_days_1', 'work_hub', 'connection_from', 'connection_to']
    search_fields = ['route_id', 'route']
    list_filter = ['route_type', 'work_hub', 'operating_days_1']
    inlines = [StmPickupPointInline, StmShiftTimeInline]
    actions = ['mark_as_active', 'mark_as_inactive']

    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected routes have been marked as active.")
    mark_as_active.short_description = "Mark selected routes as active"

    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected routes have been marked as inactive.")
    mark_as_inactive.short_description = "Mark selected routes as inactive"


# Register StmPickupPoint model
@admin.register(StmPickupPoint)
class StmPickupPointAdmin(admin.ModelAdmin):
    list_display = ['route', 'stop_id', 'pick_up_point', 'pick_up_point_order_id']
    search_fields = ['route__route', 'stop_id', 'pick_up_point']
    ordering = ['pick_up_point_order_id']
    list_filter = ['route']


# Register StmShiftTime model
@admin.register(StmShiftTime)
class StmShiftTimeAdmin(admin.ModelAdmin):
    list_display = ['route', 'time', 'special_time', 'shift_time', 'stop_order']
    search_fields = ['route__route', 'shift_time']
    list_filter = ['route', 'time', 'shift_time']
    ordering = ['shift_time', 'stop_order']


from django.contrib import admin
from .models import BusMasterList  # Import your model

# Register the BusMasterList model with the admin site
@admin.register(BusMasterList)
class BusMasterListAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ('bus_no', 'capacity')

    # Enable search functionality
    search_fields = ('bus_no',)

    # Add filters for quick filtering
    list_filter = ('capacity',)

    # Optional: Define how many items to show per page
    list_per_page = 25

    # Optional: Ensure bus_no is stripped of whitespace on save
    def save_model(self, request, obj, form, change):
        obj.bus_no = obj.bus_no.strip()  # Remove leading/trailing whitespace
        super().save_model(request, obj, form, change)



from django.contrib import admin
from .models import Unit, EKSTMDailyTrips, EKSTMMileage, EKSTMSalik

# Register Unit model
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('code',)
    search_fields = ('code',)
    ordering = ('code',)

# Register EKSTMDailyTrips model
@admin.register(EKSTMDailyTrips)
class EKSTMDailyTripsAdmin(admin.ModelAdmin):
    list_display = ('unit', 'route_id', 'ride_date', 'route_type', 'shift_in', 'shift_out', 'route_group', 'driver_name')
    search_fields = ('unit__code', 'route_id', 'driver_name', 'route_group')
    list_filter = ('ride_date', 'route_type', 'route_group')
    ordering = ('-ride_date', 'unit')
    date_hierarchy = 'ride_date'  # Adds a date-based navigation

    # Optional: Improve readability of foreign key field in forms
    autocomplete_fields = ('unit',)

# Register EKSTMMileage model
@admin.register(EKSTMMileage)
class EKSTMMileageAdmin(admin.ModelAdmin):
    list_display = ('unit', 'mileage', 'date')
    search_fields = ('unit__code', 'mileage')
    list_filter = ('date',)
    ordering = ('-date', 'unit')
    date_hierarchy = 'date'  # Adds a date-based navigation

    # Optional: Improve readability of foreign key field in forms
    autocomplete_fields = ('unit',)

# Register EKSTMSalik model
@admin.register(EKSTMSalik)
class EKSTMSalikAdmin(admin.ModelAdmin):
    list_display = ('unit', 'routeid', 'salik_start_date', 'salik_satrt_time', 'routetype', 'routegroup', 'driver_name')
    search_fields = ('unit__code', 'routeid', 'driver_name', 'routegroup')
    list_filter = ('salik_start_date', 'routetype', 'routegroup')
    ordering = ('-salik_start_date', 'unit')
    date_hierarchy = 'salik_start_date'  # Adds a date-based navigation

    # Optional: Improve readability of foreign key field in forms
    autocomplete_fields = ('unit',)