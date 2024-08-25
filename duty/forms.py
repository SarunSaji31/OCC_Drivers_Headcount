from django import forms
from django.forms import formset_factory
from .models import DriverTrip, DriverImportLog
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

# Form for handling driver trip entries
class DriverTripForm(forms.ModelForm):
    class Meta:
        model = DriverTrip
        fields = [
            'route_name', 'pick_up_time', 'drop_off_time',
            'shift_time', 'head_count', 'trip_type', 'date'
        ]
        widgets = {
            'route_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Route Name'}),
            'pick_up_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM'}),
            'drop_off_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM'}),
            'shift_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM'}),
            'head_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Head Count'}),
            'trip_type': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

# Formset for handling multiple driver trip entries
DriverTripFormSet = formset_factory(DriverTripForm, extra=1)

# Custom user creation form for handling staff ID as the username
class CustomUserCreationForm(UserCreationForm):
    staff_id = forms.CharField(
        max_length=150, 
        required=True, 
        help_text='Enter your staff ID. Required.'
    )

    class Meta:
        model = User
        fields = ['staff_id', 'password1', 'password2']

    def clean_staff_id(self):
        staff_id = self.cleaned_data.get('staff_id')
        # Check if the staff ID exists in the DriverImportLog model
        if not DriverImportLog.objects.filter(staff_id=staff_id).exists():
            raise forms.ValidationError("This staff ID does not exist in the system.")
        return staff_id

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set the staff ID as the username for the user
        user.username = self.cleaned_data['staff_id']
        if commit:
            user.save()
        return user
