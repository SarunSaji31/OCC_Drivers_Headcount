from django import forms
from .models import DutyCard

class DutyCardForm(forms.ModelForm):
    class Meta:
        model = DutyCard
        fields = ['driver_name', 'staff_id', 'duty_card_no', 'route_name', 'pick_up_time', 'drop_off_time', 'shift_time', 'head_count']
        widgets = {
            'pick_up_time': forms.TimeInput(attrs={'type': 'time'}),
            'drop_off_time': forms.TimeInput(attrs={'type': 'time'}),
            'shift_time': forms.TimeInput(attrs={'type': 'time'}),
        }
