from django.db import models

class DriverImportLog(models.Model):
    driver_name = models.CharField(max_length=100)
    staff_id = models.CharField(max_length=100, unique=True)  # Ensure staff_id is unique

    def __str__(self):
        return self.driver_name


class DutyCardTrip(models.Model):
    INBOUND_OUTBOUND_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]

    duty_card_no = models.CharField(max_length=100, unique=True)  # Ensure duty_card_no is unique
    route_name = models.CharField(max_length=255)
    trip_type = models.CharField(max_length=8, choices=INBOUND_OUTBOUND_CHOICES)
    pick_up_time = models.TimeField()
    drop_off_time = models.TimeField()
    shift_time = models.TimeField()

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
