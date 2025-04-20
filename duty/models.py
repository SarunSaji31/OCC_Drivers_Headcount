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
    report_datetime = models.DateTimeField(auto_now_add=True)
    breakdown_datetime = models.DateTimeField()
    location = models.CharField(max_length=255)
    route_number = models.CharField(max_length=100)
    trip_work_order = models.CharField(max_length=100)
    passengers_involved = models.PositiveIntegerField()
    ek_staff_numbers = models.TextField(blank=True, null=True)
    non_ek_passenger_details = models.TextField(blank=True, null=True)
    injured_passengers = models.PositiveIntegerField(default=0)
    action_taken_for_injured = models.TextField(blank=True, null=True)
    vehicle_damage = models.BooleanField(default=False)
    driver_name = models.CharField(max_length=100)
    driver_id = models.CharField(max_length=100)
    driver_shift = models.CharField(max_length=100)
    breakdown_description = models.TextField()
    ek_vehicles_involved = models.PositiveIntegerField(default=0)
    vehicle_make_plate = models.CharField(max_length=100)
    replacement_vehicle = models.CharField(max_length=100, blank=True, null=True)
    reported_to_person = models.CharField(max_length=100)
    reported_datetime = models.DateTimeField()

    def __str__(self):
        return f"Breakdown Report {self.id} - {self.breakdown_datetime}"

class StmRoute(models.Model):
    route_id = models.CharField(max_length=50, unique=True, db_column='R_id')
    route = models.CharField(max_length=50, db_column='Route')
    route_type = models.CharField(max_length=50, db_column='Type')
    operating_days_1 = models.CharField(max_length=7, db_column='Operating_days_1')
    operating_days_2 = models.CharField(max_length=7, blank=True, null=True, db_column='Operating_days_2')
    work_hub = models.CharField(max_length=255, db_column='Work_Hub')
    connection_from = models.CharField(max_length=255, db_column='Connection_From', null=True, blank=True)
    connection_to = models.CharField(max_length=255, db_column='Connection_To', null=True, blank=True)

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
    stop_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Route {self.route.route}, Shift Time: {self.shift_time}"

    class Meta:
        db_table = 'Stm_ShiftTime'
        ordering = ['stop_order', 'time']

class BusKmTracking(models.Model):
    duty_card = models.ForeignKey(
        DutyCardTrip, 
        on_delete=models.CASCADE, 
        related_name='bus_km_tracking',
        verbose_name="Duty Card",
        null=True,
        blank=True
    )
    duty_card_no = models.CharField(
        max_length=100,
        verbose_name="Duty Card No",
        blank=True,
        editable=True
    )
    driver = models.ForeignKey(
        DriverImportLog, 
        on_delete=models.CASCADE, 
        related_name='bus_km_tracking',
        verbose_name="Driver",
        null=True,
        blank=True
    )
    submission_date = models.DateField(null=True, blank=True, verbose_name="Submission Date")
    bus_no = models.CharField(max_length=20, verbose_name="Bus Number")
    start_km = models.PositiveIntegerField(verbose_name="Start Kilometer")
    end_km = models.PositiveIntegerField(verbose_name="End Kilometer")
    bus_change = models.BooleanField(default=False, verbose_name="Bus Changed (Optional)")
    bus_start_time = models.TimeField(null=True, blank=True, verbose_name="Bus Start Time")
    bus_end_time = models.TimeField(null=True, blank=True, verbose_name="Bus End Time")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Start Time Change (Optional)")
    end_time = models.TimeField(null=True, blank=True, verbose_name="End Time Change (Optional)")
    start_km_change = models.PositiveIntegerField(null=True, blank=True, verbose_name="Start Kilometer Change (Optional)")
    end_km_change = models.PositiveIntegerField(null=True, blank=True, verbose_name="End Kilometer Change (Optional)")
    changed_bus_no = models.CharField(
        max_length=20,
        verbose_name="Changed Bus Number",
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        if self.duty_card and not self.duty_card_no:
            self.duty_card_no = self.duty_card.duty_card_no
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Bus {self.bus_no} - Start: {self.start_km}, End: {self.end_km}"

class BusMasterList(models.Model):
    bus_no = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Bus Number"
    )
    capacity = models.IntegerField(
        verbose_name="Capacity"
    )

    def __str__(self):
        return self.bus_no

    class Meta:
        db_table = 'bus_master_list'
        verbose_name = "Bus Master Entry"
        verbose_name_plural = "Bus Master List"



class Unit(models.Model):
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.code

    class Meta:
        db_table = 'duty_unit'

class EKSTMDailyTrips(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, to_field='code')
    routetime = models.CharField(max_length=50)
    shift_out = models.CharField(max_length=50, blank=True, null=True)  # CSV header: shift_Out
    shift_in = models.CharField(max_length=50, blank=True, null=True)
    ride_date = models.DateField()
    first_point = models.CharField(max_length=100)
    route_id = models.CharField(max_length=50)
    route_group = models.CharField(max_length=50)
    route_type = models.CharField(max_length=20)
    driver_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.unit} - {self.route_id} - {self.ride_date}"

    class Meta:
        db_table = 'EKSTM_daily_trips'


class EKSTMMileage(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, to_field='code')
    mileage = models.CharField(max_length=50)
    date = models.DateField()  # Removed default=date.today

    def __str__(self):
        return f"{self.unit} - {self.mileage} ({self.date})"

    class Meta:
        db_table = 'EKSTM_mileage'

class EKSTMSalik(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, to_field='code')
    salik_start_date = models.DateField()
    salik_satrt_time = models.CharField(max_length=20)  # Note: Typo 'satrt' should be 'start'
    initial_location = models.CharField(max_length=100)
    final_location = models.CharField(max_length=100)
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    crossing_rate = models.CharField(max_length=20)
    routeid = models.CharField(max_length=50)
    routetype = models.CharField(max_length=50)
    shift_in = models.CharField(max_length=50, blank=True, null=True)
    shift_out = models.CharField(max_length=50, blank=True, null=True)
    routegroup = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.unit} - {self.routeid} - {self.salik_start_date}"

    class Meta:
        db_table = 'EKSTM_salik'

from django.db import models
from .models import DriverImportLog

class DriverProfile(models.Model):
    driver = models.OneToOneField(DriverImportLog, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    mobile_no = models.CharField(max_length=15, null=True, blank=True)
    secondary_contact_no = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    # Profile Picture
    picture = models.CharField(max_length=255, null=True, blank=True)  # Google Drive file ID
    
    # Driving License Details
    license_no = models.CharField(max_length=50, null=True, blank=True)
    license_issue_date = models.DateField(null=True, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    license_place_of_issue = models.CharField(max_length=100, null=True, blank=True)
    license_front_file_id = models.CharField(max_length=255, null=True, blank=True)
    license_back_file_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Emirates ID Details
    eid_no = models.CharField(max_length=50, null=True, blank=True)
    eid_issue_date = models.DateField(null=True, blank=True)
    eid_expiry_date = models.DateField(null=True, blank=True)
    eid_nationality = models.CharField(max_length=100, null=True, blank=True)
    eid_front_file_id = models.CharField(max_length=255, null=True, blank=True)
    eid_back_file_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Passport Details
    passport_no = models.CharField(max_length=50, null=True, blank=True)
    passport_issue_date = models.DateField(null=True, blank=True)
    passport_expiry_date = models.DateField(null=True, blank=True)
    passport_front_file_id = models.CharField(max_length=255, null=True, blank=True)
    passport_back_file_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Profile for {self.driver.driver_name}"