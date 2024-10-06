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
    date = models.DateField(auto_now_add=True)  # Default current date
    route = models.CharField(max_length=255)
    in_out = models.CharField(max_length=50, choices=[('IN', 'IN'), ('OUT', 'OUT')])
    std = models.TimeField()  # Scheduled Time of Departure
    atd = models.TimeField()  # Actual Time of Departure
    sta = models.TimeField()  # Scheduled Time of Arrival
    ata = models.TimeField()  # Actual Time of Arrival
    delay = models.IntegerField()  # Consider DurationField if you need more precision
    staff_count = models.IntegerField()
    remarks = models.TextField(blank=True, null=True)  # Optional remarks

    def __str__(self):
        return f"Delay on {self.date} for Route {self.route}"

class BreakdownData(models.Model):
    date = models.DateField(auto_now_add=True)
    route = models.CharField(max_length=255)
    in_out = models.CharField(max_length=50, choices=[('IN', 'IN'), ('OUT', 'OUT')])
    breakdown_time = models.TimeField()
    breakdown_location = models.CharField(max_length=255)  # Updated to snake_case
    bus_no = models.CharField(max_length=50)
    issue = models.TextField()
    driver_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=100)
    staff_count = models.IntegerField()
    replacement_driver = models.CharField(max_length=255, blank=True, null=True)  # Make optional if sometimes there’s no replacement
    replacement_bus = models.CharField(max_length=50, blank=True, null=True)  # Make optional
    report_to_ek = models.BooleanField(default=False)

    def __str__(self):
        return f"Breakdown on {self.date} for Route {self.route}"

class AccidentsData(models.Model):
    date = models.DateField(auto_now_add=True)
    route = models.CharField(max_length=255)
    in_out = models.CharField(max_length=50, choices=[('IN', 'IN'), ('OUT', 'OUT')])
    accident_time = models.TimeField()
    accident_location = models.CharField(max_length=255)  # Updated to snake_case
    bus_no = models.CharField(max_length=50)
    accident_issue = models.TextField()
    driver_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=100)
    staff_count = models.IntegerField()
    replacement_driver = models.CharField(max_length=255, blank=True, null=True)  # Make optional
    replacement_bus = models.CharField(max_length=50, blank=True, null=True)  # Make optional
    report_to_ek = models.BooleanField(default=False)

    def __str__(self):
        return f"Accident on {self.date} for Route {self.route}"