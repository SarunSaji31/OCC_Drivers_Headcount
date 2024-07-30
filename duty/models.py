# duty/models.py

from django.db import models

class Driver(models.Model):
    driver_name = models.CharField(max_length=100)
    staff_id = models.CharField(max_length=100)
    duty_card_no = models.CharField(max_length=100)

    def __str__(self):
        return self.driver_name

class Trip(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='trips')
    route_name = models.CharField(max_length=100)
    pick_up_time = models.TimeField()
    drop_off_time = models.TimeField()
    shift_time = models.TimeField()
    head_count = models.IntegerField()
    
    def __str__(self):
        return self.route_name
