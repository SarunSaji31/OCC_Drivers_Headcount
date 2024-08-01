from django import forms
from .models import DriverTrip

class DriverTripForm(forms.ModelForm):
    class Meta:
        model = DriverTrip
        fields = ['staff_id', 'driver_name', 'duty_card_no', 'route_name', 'pick_up_time', 'drop_off_time', 'shift_time', 'head_count', 'trip_type']
        labels = {
            'staff_id': 'Staff ID',
            'driver_name': 'Driver Name',
            'duty_card_no': 'Duty Card No',
            'route_name': 'Route Name',
            'pick_up_time': 'Pick Up Time',
            'drop_off_time': 'Drop Off Time',
            'shift_time': 'Shift Time',
            'head_count': 'Head Count',
            'trip_type': 'Type',
        }
        widgets = {
            'staff_id': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'duty_card_no': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'route_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'pick_up_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'required': 'required'}),
            'drop_off_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'required': 'required'}),
            'shift_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'required': 'required'}),
            'head_count': forms.NumberInput(attrs={'class': 'form-control', 'required': 'required'}),
            'trip_type': forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
        }
