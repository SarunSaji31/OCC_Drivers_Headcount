from django.db import models

class DriverTrip(models.Model):
    INBOUND_OUTBOUND_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]

    staff_id = models.CharField(max_length=100)
    driver_name = models.CharField(max_length=100)
    duty_card_no = models.CharField(max_length=100)
    route_name = models.CharField(max_length=100)
    pick_up_time = models.TimeField()
    drop_off_time = models.TimeField()
    shift_time = models.TimeField()
    head_count = models.IntegerField()
    trip_type = models.CharField(max_length=8, choices=INBOUND_OUTBOUND_CHOICES, default='inbound')

    def __str__(self):
        return self.driver_name

class DriverImportLog(models.Model):
    driver_name = models.CharField(max_length=100)
    staff_id = models.CharField(max_length=100)

    def __str__(self):
        return self.driver_name

class DutyCardTrip(models.Model):
    duty_card_no = models.CharField(max_length=100)
    route_name = models.CharField(max_length=255)
    pick_up_time = models.TimeField()
    drop_off_time = models.TimeField()

    def __str__(self):
        return self.duty_card_no
