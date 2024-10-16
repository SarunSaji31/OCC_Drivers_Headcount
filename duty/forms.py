from django import forms
from django.forms import formset_factory
from .models import DriverTrip, DriverImportLog
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import DelayData
from .models import BreakdownReport

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
    

# forms.py
class DelayDataForm(forms.ModelForm):
    class Meta:
        model = DelayData
        fields = ['route', 'in_out', 'std', 'atd', 'sta', 'ata', 'staff_count', 'remarks']  




class DelayDataForm(forms.ModelForm):
    class Meta:
        model = DelayData
        fields = ['route', 'in_out', 'std', 'atd', 'sta', 'ata', 'staff_count', 'remarks']  

class BreakdownReportForm(forms.ModelForm):
    class Meta:
        model = BreakdownReport
        fields = [
            'reported_datetime',  # Matches "Date and Time of Report" in the front-end
            'breakdown_datetime',  # Matches "Breakdown Date and Time"
            'location',  # Matches "Breakdown Location with the nearest landmark"
            'route_number',  # Matches "Route #"
            'trip_work_order',  # Matches "Trip Work Order #"
            'passengers_involved',  # Matches "No. of passengers involved"
            'non_ek_passenger_details',  # Matches "Non-EK Passenger Details"
            'injured_passengers',  # Matches "No. of injured passengers"
            'action_taken_for_injured',  # Matches "Action taken for injured passenger"
            'vehicle_damage',  # Matches "Damage to the vehicle(s)" (Yes/No)
            'driver_name',  # Matches "Driver Name"
            'driver_id',  # Matches "Driver ID"
            'driver_shift',  # Matches "Driver Shift"
            'breakdown_description',  # Matches "Description of the Breakdown"
            'ek_vehicles_involved',  # Matches "No. of EK vehicles involved"
            'vehicle_make_plate',  # Matches "Vehicle Make and Plate #"
            'replacement_vehicle',  # Matches "Replacement vehicle #"
            'reported_to_person',  # Matches "Reported to person at EK"
        ]
        widgets = {
            'reported_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'breakdown_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'vehicle_damage': forms.Select(choices=[('yes', 'Yes'), ('no', 'No')]),  # Dropdown for Yes/No
        }
