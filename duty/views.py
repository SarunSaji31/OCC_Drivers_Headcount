from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from datetime import datetime, timedelta,date
import pandas as pd
import logging
from functools import wraps
from django.db.models import Sum

from .forms import DriverTripFormSet, CustomUserCreationForm, PasswordResetRequestForm, SetNewPasswordForm
from .models import DriverTrip, DriverImportLog, DutyCardTrip
from .decorators import user_in_driverimportlog_required

# Setup logger
logger = logging.getLogger(__name__)

@login_required
def home(request):
    # Fetch the staff name using the logged-in user's username (assumed to be their staff ID)
    staff_id = request.user.username
    staff_name = DriverImportLog.objects.filter(staff_id=staff_id).values_list('driver_name', flat=True).first()
    
    if not staff_name:
        staff_name = request.user.username  # Fallback to username if staff name is not found

    # Example of converting datetime to string
    driver_trips = DriverTrip.objects.filter(driver__staff_id=staff_id)
    driver_trip_data = []
    for trip in driver_trips:
        trip_data = {
            'route_name': trip.route_name,
            'pick_up_time': trip.pick_up_time.strftime('%H:%M:%S'),  # Convert time to string
            'drop_off_time': trip.drop_off_time.strftime('%H:%M:%S'),  # Convert time to string
            'shift_time': trip.shift_time.strftime('%H:%M:%S'),  # Convert time to string
            'head_count': trip.head_count,
            'trip_type': trip.trip_type,
            'date': trip.date.strftime('%Y-%m-%d')  # Convert date to string
        }
        driver_trip_data.append(trip_data)

    context = {
        'staff_name': staff_name,
        'driver_trips': driver_trip_data,
    }

    return render(request, 'duty/home.html', context)

@login_required
def enter_head_count(request):
    # Fetch the staff name using the logged-in user's username (assumed to be their staff ID)
    staff_id = request.user.username
    driver = DriverImportLog.objects.filter(staff_id=staff_id).first()

    # Check if driver is None
    if not driver:
        return render(request, 'duty/enter_head_count.html', {
            'error_message': "Driver information not found. Please contact support.",
        })

    staff_name = driver.driver_name if driver else request.user.username  # Fallback to username if staff name is not found

    if request.method == 'POST':
        trip_formset = DriverTripFormSet(request.POST, prefix='drivertrip_set')

        duty_card_no = request.POST.get('duty_card_no')
        duty_card = DutyCardTrip.objects.filter(duty_card_no=duty_card_no).first()

        if not duty_card_no:
            return render(request, 'duty/enter_head_count.html', {  
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Please fill in the Duty Card No.",
            })

        # Allow the user to select a date for the trip (from the form)
        desired_date = datetime.strptime(request.POST.get('drivertrip_set-0-date'), '%Y-%m-%d').date()

        # Check if the user has already submitted a duty card on the selected date
        existing_trip = DriverTrip.objects.filter(driver=driver, date=desired_date).first()
        if existing_trip:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': f"You have already added duty card {existing_trip.duty_card.duty_card_no} for {desired_date}. You cannot add multiple duty cards for the same date.",
            })

        # Process the form submission and save trips
        if trip_formset.is_valid():
            for form in trip_formset:
                trip = form.save(commit=False)
                trip.driver = driver  # Assign the driver object to the trip
                trip.duty_card = duty_card  # Assign the duty card
                trip.save()

            messages.success(request, "Headcount successfully submitted.")
            return redirect('success')
        else:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Please correct the errors below.",
            })

    else:
        trip_formset = DriverTripFormSet(prefix='drivertrip_set')

    return render(request, 'duty/enter_head_count.html', {
        'trip_formset': trip_formset,
        'staff_name': staff_name,
    })


@login_required
def success(request):
    return render(request, 'duty/success.html')

def user_in_driverimportlog_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Deny access if the user's staff ID exists in the DriverImportLog table
        if DriverImportLog.objects.filter(staff_id=request.user.username).exists():
            return render(request, 'duty/access_denied.html')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@user_in_driverimportlog_required  # Apply the custom decorator here
def report_view(request):
    # Your view logic here...
    date_range = request.GET.get('daterange')
    route_filter = request.GET.get('route')
    shift_time_filter = request.GET.get('shift_time')
    trip_type_filter = request.GET.get('trip_type')

    driver_trips = DriverTrip.objects.all()

    if date_range:
        try:
            start_date, end_date = date_range.split(' - ')
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            driver_trips = driver_trips.filter(date__range=(start_date, end_date))
        except ValueError as e:
            driver_trips = driver_trips.none()

    if route_filter:
        driver_trips = DriverTrip.objects.filter(route_name__icontains=route_filter)

    if shift_time_filter:
        try:
            parsed_shift_time = datetime.strptime(shift_time_filter, '%H:%M').time()
            driver_trips = driver_trips.filter(shift_time=parsed_shift_time)
        except ValueError:
            driver_trips = driver_trips.none()

    if trip_type_filter:
        driver_trips = driver_trips.filter(trip_type__iexact=trip_type_filter)

    routes = driver_trips.values_list('route_name', flat=True).distinct()
    shift_times = driver_trips.values_list('shift_time', flat=True).distinct()

    context = {
        'driver_trips': driver_trips,
        'routes': routes,
        'shift_times': shift_times,
    }

    return render(request, 'duty/report_data.html', context)


def download_report(request):
    date_range = request.GET.get('daterange')
    route_filter = request.GET.get('route')
    shift_time_filter = request.GET.get('shift_time')
    trip_type_filter = request.GET.get('trip_type')

    driver_trips = DriverTrip.objects.all()

    if date_range:
        try:
            start_date, end_date = date_range.split(' - ')
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            driver_trips = driver_trips.filter(date__range=(start_date, end_date))
        except ValueError:
            driver_trips = driver_trips.none()

    if route_filter:
        driver_trips = driver_trips.filter(route_name=route_filter)
    if shift_time_filter:
        driver_trips = driver_trips.filter(shift_time=shift_time_filter)
    if trip_type_filter:
        driver_trips = driver_trips.filter(trip_type=trip_type_filter)

    data = []
    for trip in driver_trips:
        data.append({
            'Staff ID': trip.driver.staff_id,
            'Driver Name': trip.driver.driver_name,
            'Duty Card No': trip.duty_card.duty_card_no,
            'Route Name': trip.route_name,
            'Pick Up Time': trip.pick_up_time.strftime("%H:%M"),
            'Drop Off Time': trip.drop_off_time.strftime("%H:%M"),
            'Shift Time': trip.shift_time.strftime("%H:%M"),
            'Trip Type': trip.trip_type,
            'Date': trip.date.strftime("%Y-%m-%d"),
            'Head Count': trip.head_count,
        })

    df = pd.DataFrame(data)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=driver_trip_report_{date_range}.xlsx'

    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Driver Trips', index=False)

    return response


def staff_id_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
        qs = DriverImportLog.objects.filter(staff_id__icontains=term)
        staff_ids = list(qs.values_list('staff_id', flat=True))
        return JsonResponse(staff_ids, safe=False)
    return JsonResponse([], safe=False)

def get_driver_name(request):
    staff_id = request.GET.get('staff_id', None)
    if staff_id:
        driver_log = DriverImportLog.objects.filter(staff_id=staff_id).first()
        if driver_log:
            return JsonResponse({'driver_name': driver_log.driver_name})
        else:
            return JsonResponse({'driver_name': ''})
    return JsonResponse({'driver_name': ''})

def duty_card_no_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
        qs = DutyCardTrip.objects.filter(duty_card_no__icontains=term).values_list('duty_card_no', flat=True)
        duty_card_nos = list(set(qs))
        return JsonResponse(duty_card_nos, safe=False)
    
def get_duty_card_details(request):
    if 'duty_card_no' in request.GET:
        duty_card_no = request.GET.get('duty_card_no')
        #print(f"Received duty_card_no: {duty_card_no}")

        # Fetching trips from the database
        trips = DutyCardTrip.objects.filter(duty_card_no=duty_card_no)

        if not trips.exists():
            return JsonResponse({'error': 'No trips found for the provided duty card number.'}, status=404)

        trip_details = []
        for trip in trips:
            # Convert trip_type to match the expected values in the frontend
            normalized_trip_type = 'inbound' if trip.trip_type == 'IN' else 'outbound'

            trip_info = {
                'route_name': trip.route_name,
                'pick_up_time': trip.pick_up_time.strftime("%H:%M") if trip.pick_up_time else '',
                'drop_off_time': trip.drop_off_time.strftime("%H:%M") if trip.drop_off_time else '',
                'shift_time': trip.shift_time.strftime("%H:%M") if trip.shift_time else '',
                'trip_type': normalized_trip_type,
                'date': trip.date.strftime("%Y-%m-%d") if hasattr(trip, 'date') else datetime.today().strftime("%Y-%m-%d"),
                'head_count': trip.head_count if hasattr(trip, 'head_count') else 0  # Add other fields as needed
            }
            #print(f"Processed trip: {trip_info}")
            trip_details.append(trip_info)

        #print(f"Returning trip details: {trip_details}")
        return JsonResponse({'trips': trip_details}, safe=False)

    print("No duty_card_no provided in request.")
    return JsonResponse({'error': 'Duty card number not provided'}, status=400)

@login_required
def route_autocomplete(request):
    if 'term' in request.GET:
        qs = DriverTrip.objects.filter(route_name__istartswith=request.GET.get('term'))
        routes = list(qs.values_list('route_name', flat=True).distinct())
        return JsonResponse(routes, safe=False)
    return JsonResponse([], safe=False)

@login_required
def shift_time_autocomplete(request):
    if 'term' in request.GET:
        shift_time_term = request.GET.get('term')

        # Ensure the term is in a valid time format like "HH:MM"
        try:
            # Check if the term is in "HH:MM" format
            parsed_time = datetime.strptime(shift_time_term, "%H:%M").time()
            qs = DriverTrip.objects.filter(shift_time__startswith=parsed_time)
            shift_times = new_func(qs)
            shift_times = [time.strftime("%H:%M") for time in shift_times]
        except ValueError:
            shift_times = []

        return JsonResponse(shift_times, safe=False)
    
    return JsonResponse([], safe=False)

def new_func(qs):
    shift_times = list(qs.values_list('shift_time', flat=True).distinct())
    return shift_times

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            logger.debug("Form is valid, saving user.")
            user = form.save()
            messages.success(request, 'Your account has been created successfully! Please log in.')
            return redirect('login')  # Redirect to the login page
        else:
            logger.warning("Form is not valid.")
    else:
        logger.debug("GET request, rendering signup form.")
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('login')


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            staff_id = form.cleaned_data['staff_id']
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(username=staff_id)
                # Check if email matches the one associated with the user
                if user.email == email:
                    # Redirect to a password reset form
                    return redirect(reverse('set_new_password', args=[user.id]))
                else:
                    messages.error(request, 'The email address does not match our records.')
            except User.DoesNotExist:
                messages.error(request, 'No user found with that Staff ID.')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'registration/password_reset_request.html', {'form': form})

def set_new_password(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.password = make_password(new_password)
            user.save()
            messages.success(request, 'Your password has been reset successfully.')
            return redirect('login')
    else:
        form = SetNewPasswordForm()

    return render(request, 'registration/set_new_password.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Check if "Remember Me" was checked
                if request.POST.get('remember_me'):
                    request.session.set_expiry(1209600)  # 2 weeks
                    request.session['remember_me'] = True
                else:
                    request.session.set_expiry(300)  # 5 minutes
                    request.session['remember_me'] = False
                
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, "login.html", {"form": form})

@user_in_driverimportlog_required  # Apply custom decorator
def dashboard_data(request):
    """
    Returns staff load data based on filters like date, shift time, and type.
    """
    date_filter = request.GET.get('date')
    shift_filter = request.GET.get('shift')
    type_filter = request.GET.get('type')

    if not date_filter:
        date_filter = date.today()

    trips = DriverTrip.objects.filter(date=date_filter)

    if shift_filter:
        trips = trips.filter(shift_time=shift_filter)
    
    if type_filter:
        trips = trips.filter(trip_type=type_filter)

    total_staff = trips.aggregate(total_head_count=Sum('head_count'))['total_head_count'] or 0
    total_gd_staff = trips.filter(route_name__startswith='GD').aggregate(Sum('head_count'))['head_count__sum'] or 0
    total_gk_staff = trips.filter(route_name__startswith='GK').aggregate(Sum('head_count'))['head_count__sum'] or 0
    total_ge_staff = trips.filter(route_name__startswith='GE').aggregate(Sum('head_count'))['head_count__sum'] or 0
    total_dwc_staff = trips.filter(route_name__startswith='DWC').aggregate(Sum('head_count'))['head_count__sum'] or 0
    total_cc_staff = trips.filter(route_name__startswith='CC').aggregate(Sum('head_count'))['head_count__sum'] or 0

    data = {
        'total_staff': total_staff,
        'gd_staff': total_gd_staff,
        'gk_staff': total_gk_staff,
        'ge_staff': total_ge_staff,
        'dwc_staff': total_dwc_staff,
        'cc_staff': total_cc_staff,
    }

    return JsonResponse(data)

def duty_card_submission_data(request):
    # Get the date filter from the request or default to today's date
    date_filter = request.GET.get('date', datetime.today().strftime('%Y-%m-%d'))

    # Check if the user requested an Excel download
    if request.GET.get('download') == 'xlsx':
        return download_duty_card_data_as_excel(date_filter)

    # Create aware datetime range for the selected date
    date_filter_start = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.min.time()))
    date_filter_end = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.max.time()))

    # Fetch all unique duty cards from DutyCardTrip (total duty cards)
    duty_card_trips = DutyCardTrip.objects.values('duty_card_no').distinct()
    total_duty_cards = duty_card_trips.count()

    # Fetch all unique submitted duty cards from DriverTrip (submitted duty cards)
    submitted_duty_cards = DriverTrip.objects.filter(date__range=(date_filter_start, date_filter_end)).values('duty_card').distinct()
    submitted_cards = submitted_duty_cards.count()

    # Calculate pending cards
    pending_cards = total_duty_cards - submitted_cards if total_duty_cards > submitted_cards else 0

    # Return the data for the chart
    data = {
        'total_duty_cards': total_duty_cards,
        'submitted_cards': submitted_cards,
        'pending_cards': pending_cards,
    }

    return JsonResponse(data)


def download_duty_card_data_as_excel(date_filter):
    # Create aware datetime range for the selected date
    date_filter_start = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.min.time()))
    date_filter_end = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.max.time()))

    # Fetch all unique duty cards from DutyCardTrip
    duty_card_trips = DutyCardTrip.objects.values('duty_card_no').distinct()

    # Fetch submitted duty cards from DriverTrip (based on the selected date)
    submitted_duty_cards = DriverTrip.objects.filter(date__range=(date_filter_start, date_filter_end)).values('duty_card__duty_card_no').distinct()

    # Prepare data for Excel
    data = []
    for duty_card in duty_card_trips:
        duty_card_no = duty_card['duty_card_no']

        # Check if the duty card was submitted by looking at the submitted duty cards
        is_submitted = submitted_duty_cards.filter(duty_card__duty_card_no=duty_card_no).exists()

        data.append({
            'Duty Card No': duty_card_no,
            'Submission Status': 'Submitted' if is_submitted else 'Pending',
            'Date': date_filter  # We use the provided date as there's no date in DutyCardTrip
        })

    # Create DataFrame
    df = pd.DataFrame(data)

    # Generate the Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=duty_card_details_{date_filter}.xlsx'

    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Duty Cards', index=False)

    return response

@user_in_driverimportlog_required
@login_required
def admin_dashboard(request):
    return render(request, 'duty/admin_dashboard.html')
