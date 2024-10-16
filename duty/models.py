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
    submission_date = models.DateTimeField(null=True, blank=True)  # Track when the card was submitted
    def __str__(self):
        return self.duty_card_no


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
    date = models.DateField(auto_now_add=True)
    route = models.CharField(max_length=255)
    in_out = models.CharField(max_length=50, choices=[('IN', 'IN'), ('OUT', 'OUT')])
    std = models.TimeField()  
    atd = models.TimeField()  
    sta = models.TimeField()  
    ata = models.TimeField()  
    delay = models.CharField(max_length=8)  # Increase the length to accommodate longer delays (HH:MM)
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