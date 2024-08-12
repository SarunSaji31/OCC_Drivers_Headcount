# forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Driver, DriverTrip

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['staff_id', 'driver_name', 'duty_card_no']
        widgets = {
            'staff_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Staff ID'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Driver Name'}),
            'duty_card_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Duty Card No'}),
        }

DriverTripFormSet = inlineformset_factory(
    Driver,
    DriverTrip,
    fields=('route_name', 'pick_up_time', 'drop_off_time', 'shift_time', 'head_count', 'trip_type', 'date'),
    extra=1,
    widgets={
        'route_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Route Name'}),
        'pick_up_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM'}),
        'drop_off_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM'}),
        'shift_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM'}),
        'head_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Head Count'}),
        'trip_type': forms.Select(attrs={'class': 'form-control'}),
        'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})  # Allow manual entry
    }
)
