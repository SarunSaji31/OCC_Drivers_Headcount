from django import forms
from django.forms import formset_factory
from .models import DriverTrip, DriverImportLog
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import DelayData, BreakdownData, AccidentsData

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
            'head_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Head Count', 'min': 0, 'max': 47}),
            'trip_type': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_head_count(self):
        head_count = self.cleaned_data.get('head_count')
        if head_count is None or head_count < 0 or head_count > 47:
            raise forms.ValidationError("Head count must be between 0 and 47.")
        return head_count

# Formset for handling multiple driver trip entries
DriverTripFormSet = formset_factory(DriverTripForm, extra=1)

# Custom user creation form for handling staff ID as the username and adding an email field
class CustomUserCreationForm(UserCreationForm):
    staff_id = forms.CharField(
        max_length=150, 
        required=True, 
        help_text='Enter your staff ID. Required.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Staff ID'})
    )
    email = forms.EmailField(
        required=True,
        help_text='Enter your email address. Required.',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )

    class Meta:
        model = User
        fields = ['staff_id', 'email', 'password1', 'password2']

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
        user.email = self.cleaned_data['email']  # Save the email address
        if commit:
            user.save()
        return user

class PasswordResetRequestForm(forms.Form):
    staff_id = forms.CharField(max_length=150, label="Staff ID")
    email = forms.EmailField(label="Email")

# Form for setting a new password
class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, label="New Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data
    

# Form for Delay Data
class DelayDataForm(forms.ModelForm):
    class Meta:
        model = DelayData
        fields = ['route', 'in_out', 'std', 'atd', 'sta', 'ata', 'delay', 'staff_count', 'remarks']

# Form for Breakdown Data
class BreakdownDataForm(forms.ModelForm):
    class Meta:
        model = BreakdownData
        fields = ['route', 'in_out', 'breakdown_time', 'breakdown_location', 'bus_no', 'issue', 'driver_name', 'staff_id', 'staff_count', 'replacement_driver', 'replacement_bus', 'report_to_ek']

# Form for Accident Data
class AccidentsDataForm(forms.ModelForm):
    class Meta:
        model = AccidentsData
        fields = ['route', 'in_out', 'accident_time', 'accident_location', 'bus_no', 'accident_issue', 'driver_name', 'staff_id', 'staff_count', 'replacement_driver', 'replacement_bus', 'report_to_ek']
