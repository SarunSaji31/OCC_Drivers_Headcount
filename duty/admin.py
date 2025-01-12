from django.contrib import admin
from .models import (
    DriverImportLog, DriverTrip, DutyCardTrip, DelayData, BreakdownReport, 
    StmRoute, StmPickupPoint, StmShiftTime
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
    search_fields = ('route_name', 'trip_type', 'duty_card__duty_card_no')  # Corrected ForeignKey lookup
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
            'fields': ('head_count', 'date', 'submission_date'),
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
