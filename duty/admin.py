from django.contrib import admin
from .models import DriverImportLog, DriverTrip, DutyCardTrip, DelayData, BreakdownReport, StmRoute, StmPickupPoint, StmShiftTime

# Register DriverImportLog model
@admin.register(DriverImportLog)
class DriverImportLogAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'driver_name')
    search_fields = ('staff_id', 'driver_name')
    
    ordering = ('staff_id',)

# Register DutyCardTrip model and make the capacity field editable
@admin.register(DutyCardTrip)
class DutyCardTripAdmin(admin.ModelAdmin):
    list_display = ('duty_card_no', 'route_name', 'trip_type', 'pick_up_time', 'drop_off_time', 'shift_time', 'capacity')
    search_fields = ('duty_card_no', 'route_name')
    list_filter = ('trip_type',)
  
    ordering = ('duty_card_no',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('duty_card_no', 'route_name', 'trip_type')
        }),
        ('Timing Details', {
            'fields': ('pick_up_time', 'drop_off_time', 'shift_time')
        }),
        ('Additional Details', {
            'fields': ('capacity', 'submission_date')
        }),
    )

    # Allow the capacity field to be editable in the admin panel
    readonly_fields = ('submission_date',)  # Keep submission_date read-only if needed

# Register other models as needed
@admin.register(DriverTrip)
class DriverTripAdmin(admin.ModelAdmin):
    list_display = ('route_name', 'shift_time', 'trip_type', 'date', 'head_count')
    search_fields = ('route_name', 'trip_type')
    list_filter = ('shift_time', 'trip_type', 'date')
  
    ordering = ('-date', 'route_name')

@admin.register(DelayData)
class DelayDataAdmin(admin.ModelAdmin):
    list_display = ('route', 'date', 'std', 'atd', 'sta', 'ata', 'delay')
    search_fields = ('route',)
    list_filter = ('date', 'route')
 
    ordering = ('-date', 'route')

@admin.register(BreakdownReport)
class BreakdownReportAdmin(admin.ModelAdmin):
    list_display = ('report_datetime', 'breakdown_datetime', 'route_number', 'location', 'driver_name', 'vehicle_make_plate', 'reported_to_person')
    search_fields = ('route_number', 'driver_name', 'vehicle_make_plate', 'reported_to_person')
    list_filter = ('breakdown_datetime', 'route_number')
  
    ordering = ('-breakdown_datetime',)


from django.contrib import admin
from .models import StmRoute, StmPickupPoint, StmShiftTime

class StmPickupPointInline(admin.TabularInline):
    model = StmPickupPoint
    extra = 1
    fields = ['stop_id', 'pick_up_point', 'pick_up_point_order_id']
    ordering = ['pick_up_point_order_id']
    verbose_name = "Pickup Point"
    verbose_name_plural = "Pickup Points"

class StmShiftTimeInline(admin.TabularInline):
    model = StmShiftTime
    extra = 1
    fields = ['time', 'special_time', 'shift_time', 'stop_order']
    ordering = ['shift_time', 'stop_order']
    verbose_name = "Shift Time"
    verbose_name_plural = "Shift Times"

@admin.register(StmRoute)
class StmRouteAdmin(admin.ModelAdmin):
    list_display = ['route_id', 'route', 'route_type', 'operating_days_1', 'work_hub']
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

@admin.register(StmPickupPoint)
class StmPickupPointAdmin(admin.ModelAdmin):
    list_display = ['route', 'stop_id', 'pick_up_point', 'pick_up_point_order_id']
    search_fields = ['route__route', 'stop_id', 'pick_up_point']
    ordering = ['pick_up_point_order_id']
    list_filter = ['route']
 

@admin.register(StmShiftTime)
class StmShiftTimeAdmin(admin.ModelAdmin):
    list_display = ['route', 'time', 'special_time', 'shift_time', 'stop_order']
    search_fields = ['route__route', 'shift_time']  
    list_filter = ['route', 'time', 'shift_time']
    ordering = ['shift_time', 'stop_order']  # Ensure results are ordered by shift_time and then stop_order
 
