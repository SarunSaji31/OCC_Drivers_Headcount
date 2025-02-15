from django.db import models

class DriverImportLog(models.Model):
    driver_name = models.CharField(max_length=100)
    staff_id = models.CharField(max_length=100, unique=False)  # Ensure staff_id is unique

    def __str__(self):
        return self.driver_name


class DutyCardTrip(models.Model):
    INBOUND_OUTBOUND_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]

    duty_card_no = models.CharField(max_length=100, unique=False)  # Ensure duty_card_no is unique
    route_name = models.CharField(max_length=255)
    trip_type = models.CharField(max_length=8, choices=INBOUND_OUTBOUND_CHOICES)
    pick_up_time = models.TimeField()
    drop_off_time = models.TimeField()
    shift_time = models.TimeField()
    capacity = models.IntegerField()  # New field for bus seat capacity
    submission_date = models.DateTimeField(null=True, blank=True)  # Track when the card was submitted

    def __str__(self):
        return f"{self.duty_card_no} - {self.route_name}"


class DriverTrip(models.Model):
    INBOUND_OUTBOUND_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]

    driver = models.ForeignKey(DriverImportLog, on_delete=models.CASCADE)  # Link to DriverImportLog
    duty_card = models.ForeignKey(DutyCardTrip, on_delete=models.CASCADE)  # Link to DutyCardTrip
    route_name = models.CharField(max_length=100)
    pick_up_time = models.TimeField()
    drop_off_time = models.TimeField()
    shift_time = models.TimeField()
    head_count = models.IntegerField()
    trip_type = models.CharField(max_length=8, choices=INBOUND_OUTBOUND_CHOICES, default='inbound')
    date = models.DateField()

    def __str__(self):
        return f"{self.driver.driver_name} - {self.route_name}"


# Move DelayData out of DriverTrip so that it can be imported directly.
class DelayData(models.Model):
    date = models.DateField(null=False, blank=False, verbose_name="Date of Delay")
    route = models.CharField(max_length=255)
    in_out = models.CharField(max_length=50, choices=[('IN', 'IN'), ('OUT', 'OUT')])
    std = models.TimeField()  
    atd = models.TimeField()  
    sta = models.TimeField()  
    ata = models.TimeField()  
    delay = models.TimeField(blank=True, null=True) 
    staff_count = models.IntegerField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Delay on {self.date} for Route {self.route}"


class BreakdownReport(models.Model):
    # Section A Fields
    report_datetime = models.DateTimeField(auto_now_add=True)  # Auto-add the report submission date and time
    breakdown_datetime = models.DateTimeField()  # Breakdown date and time
    location = models.CharField(max_length=255)  # Breakdown location
    route_number = models.CharField(max_length=100)  # Route number
    trip_work_order = models.CharField(max_length=100)  # Work order number
    passengers_involved = models.PositiveIntegerField()  # Number of passengers involved
    ek_staff_numbers = models.TextField(blank=True, null=True)  # EK staff numbers
    non_ek_passenger_details = models.TextField(blank=True, null=True)  # Details of non-EK passengers
    injured_passengers = models.PositiveIntegerField(default=0)  # Number of injured passengers
    action_taken_for_injured = models.TextField(blank=True, null=True)  # Action taken for injured passengers
    vehicle_damage = models.BooleanField(default=False)  # Whether there was vehicle damage (Yes/No)
    driver_name = models.CharField(max_length=100)  # Driver's name
    driver_id = models.CharField(max_length=100)  # Driver's ID number
    driver_shift = models.CharField(max_length=100)  # Driver's shift
    breakdown_description = models.TextField()  # Description of the breakdown
    ek_vehicles_involved = models.PositiveIntegerField(default=0)  # Number of EK vehicles involved
    vehicle_make_plate = models.CharField(max_length=100)  # Vehicle make and plate number
    replacement_vehicle = models.CharField(max_length=100, blank=True, null=True)  # Replacement vehicle number (if applicable)
    reported_to_person = models.CharField(max_length=100)  # Person at EK the incident was reported to
    reported_datetime = models.DateTimeField()  # Date and time the breakdown was reported

    def __str__(self):
        return f"Breakdown Report {self.id} - {self.breakdown_datetime}" 


class StmRoute(models.Model):
    route_id = models.CharField(max_length=50, unique=True, db_column='R_id')  # Unique route ID
    route = models.CharField(max_length=50, db_column='Route')  # Route name/code
    route_type = models.CharField(max_length=50, db_column='Type')  # Type of route (Inbound/Outbound)
    operating_days_1 = models.CharField(max_length=7, db_column='Operating_days_1')  # Operating days 1, e.g., smtwtfa
    operating_days_2 = models.CharField(max_length=7, blank=True, null=True, db_column='Operating_days_2')  # Optional operating days 2
    work_hub = models.CharField(max_length=255, db_column='Work_Hub')  # Work hub for the route
    connection_from = models.CharField(max_length=255, db_column='Connection_From', null=True, blank=True)  # New field
    connection_to = models.CharField(max_length=255, db_column='Connection_To', null=True, blank=True)  # New field

    def __str__(self):
        return f'{self.route} ({self.route_type})'

    class Meta:
        db_table = 'Stm_Routes'


class StmPickupPoint(models.Model):
    route = models.ForeignKey(StmRoute, on_delete=models.CASCADE, db_column='R_id', related_name='pickup_points')
    stop_id = models.CharField(max_length=100, db_column='Stop_Id')
    pick_up_point = models.CharField(max_length=255, db_column='Pick_Up_Point')
    pick_up_point_order_id = models.IntegerField(db_column='Pick_Up_Point_Order_Id')

    def __str__(self):
        return f"Route {self.route.route} - Stop {self.stop_id} - {self.pick_up_point}"

    class Meta:
        db_table = 'Stm_Pickup_Points'
        ordering = ['pick_up_point_order_id']


class StmShiftTime(models.Model):
    route = models.ForeignKey(StmRoute, on_delete=models.CASCADE, db_column='R_id', related_name='shift_times')
    time = models.CharField(max_length=50, null=True, blank=True, db_column='Time')
    special_time = models.TimeField(null=True, blank=True, db_column='Special_Time')
    shift_time = models.TimeField(null=True, blank=True, db_column='Shift_time')
    stop_order = models.PositiveIntegerField(default=0)  # Order of pickup points

    def __str__(self):
        return f"Route {self.route.route}, Shift Time: {self.shift_time}"

    class Meta:
        db_table = 'Stm_ShiftTime'
        ordering = ['stop_order', 'time']


from django.db import models

# Ensure related models are imported if defined elsewhere:
# from .models import DutyCardTrip, DriverImportLog

class BusKmTracking(models.Model):
    duty_card = models.ForeignKey(
        DutyCardTrip, 
        on_delete=models.CASCADE, 
        related_name='bus_km_tracking',
        verbose_name="Duty Card",
        null=True,
        blank=True
    )
    # This field stores the actual duty card number for easier lookup.
    duty_card_no = models.CharField(
        max_length=100,
        verbose_name="Duty Card No",
        blank=True,
        editable=True  # Makes this field editable
    )
    driver = models.ForeignKey(
        DriverImportLog, 
        on_delete=models.CASCADE, 
        related_name='bus_km_tracking',
        verbose_name="Driver",
        null=True,
        blank=True
    )
    # New field: Submission Date – auto-populated but editable.
    submission_date = models.DateField(null=True, blank=True, verbose_name="Submission Date")
    bus_no = models.CharField(max_length=20, verbose_name="Bus Number")
    start_km = models.PositiveIntegerField(verbose_name="Start Kilometer")
    end_km = models.PositiveIntegerField(verbose_name="End Kilometer")
    bus_change = models.BooleanField(default=False, verbose_name="Bus Changed (Optional)")
    
    # New fields for basic bus times
    bus_start_time = models.TimeField(null=True, blank=True, verbose_name="Bus Start Time")
    bus_end_time = models.TimeField(null=True, blank=True, verbose_name="Bus End Time")
    
    # Fields for bus change details (store the changed times)
    start_time = models.TimeField(null=True, blank=True, verbose_name="Start Time Change (Optional)")
    end_time = models.TimeField(null=True, blank=True, verbose_name="End Time Change (Optional)")
    
    start_km_change = models.PositiveIntegerField(null=True, blank=True, verbose_name="Start Kilometer Change (Optional)")
    end_km_change = models.PositiveIntegerField(null=True, blank=True, verbose_name="End Kilometer Change (Optional)")
    
    # New field: Changed Bus Number (if bus_change is True)
    changed_bus_no = models.CharField(
        max_length=20,
        verbose_name="Changed Bus Number",
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        # Auto-populate duty_card_no from the related DutyCardTrip if available.
        if self.duty_card and not self.duty_card_no:
            self.duty_card_no = self.duty_card.duty_card_no
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Bus {self.bus_no} - Start: {self.start_km}, End: {self.end_km}"
