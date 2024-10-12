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
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from .forms import DelayDataForm,DriverTripFormSet, CustomUserCreationForm, PasswordResetRequestForm, SetNewPasswordForm,formset_factory
from .models import DriverTrip, DriverImportLog, DutyCardTrip
from .decorators import user_in_driverimportlog_required
from datetime import datetime, date
import pandas as pd
import logging
from functools import wraps
from datetime import datetime,time


# Setup logger
logger = logging.getLogger(__name__)

@login_required
def home(request):
    """Render the home page for logged-in users with driver trip details."""
    staff_id = request.user.username
    staff_name = DriverImportLog.objects.filter(staff_id=staff_id).values_list('driver_name', flat=True).first() or staff_id

    # Fetch driver trips
    driver_trips = DriverTrip.objects.filter(driver__staff_id=staff_id)
    driver_trip_data = [{
        'route_name': trip.route_name,
        'pick_up_time': trip.pick_up_time.strftime('%H:%M:%S'),
        'drop_off_time': trip.drop_off_time.strftime('%H:%M:%S'),
        'shift_time': trip.shift_time.strftime('%H:%M:%S'),
        'head_count': trip.head_count,
        'trip_type': trip.trip_type,
        'date': trip.date.strftime('%Y-%m-%d')
    } for trip in driver_trips]

    context = {
        'staff_name': staff_name,
        'driver_trips': driver_trip_data,
    }
    return render(request, 'duty/home.html', context)


@login_required
def enter_head_count(request):
    """Handle the form for entering headcount details."""
    staff_id = request.user.username
    driver = DriverImportLog.objects.filter(staff_id=staff_id).first()

    if not driver:
        return render(request, 'duty/enter_head_count.html', {
            'error_message': "Driver information not found. Please contact support."
        })

    staff_name = driver.driver_name or staff_id

    if request.method == 'POST':
        trip_formset = DriverTripFormSet(request.POST, prefix='drivertrip_set')
        duty_card_no = request.POST.get('duty_card_no')
        duty_card = DutyCardTrip.objects.filter(duty_card_no=duty_card_no).first()

        if not duty_card_no:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Please fill in the Duty Card No."
            })

        desired_date = datetime.strptime(request.POST.get('drivertrip_set-0-date'), '%Y-%m-%d').date()
        if DriverTrip.objects.filter(driver=driver, date=desired_date).exists():
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': f"Duty card already submitted for {desired_date}. Cannot submit twice for the same date."
            })

        if trip_formset.is_valid():
            for form in trip_formset:
                trip = form.save(commit=False)
                trip.driver = driver
                trip.duty_card = duty_card
                trip.save()
            messages.success(request, "Headcount successfully submitted.")
            return redirect('success')
        else:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Please correct the errors below."
            })

    trip_formset = DriverTripFormSet(prefix='drivertrip_set')
    return render(request, 'duty/enter_head_count.html', {
        'trip_formset': trip_formset,
        'staff_name': staff_name,
    })


@login_required
def success(request):
    """Render a success page after form submission."""
    return render(request, 'duty/success.html')


def user_in_driverimportlog_required(view_func):
    """Custom decorator to allow access only to users in DriverImportLog."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not DriverImportLog.objects.filter(staff_id=request.user.username).exists():
            return render(request, 'duty/access_denied.html')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@user_in_driverimportlog_required
def report_view(request):
    """Handle report generation, including DataTables server-side processing for AJAX requests."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # DataTables AJAX request handling
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')

        # Additional filters
        route_filter = request.GET.get('routeFilter', None)
        trip_type_filter = request.GET.get('tripTypeFilter', None)
        shift_time_filter = request.GET.get('shiftTimeFilter', None)
        date_range = request.GET.get('dateRange', None)

        driver_trips = DriverTrip.objects.all()

        if search_value:
            driver_trips = driver_trips.filter(
                Q(driver__staff_id__icontains=search_value) |
                Q(driver__driver_name__icontains=search_value) |
                Q(duty_card__duty_card_no__icontains=search_value) |
                Q(route_name__icontains=search_value) |
                Q(trip_type__icontains=search_value)
            )

        if route_filter:
            driver_trips = driver_trips.filter(route_name__icontains=route_filter)
        if trip_type_filter:
            driver_trips = driver_trips.filter(trip_type__iexact=trip_type_filter)
        if shift_time_filter:
            try:
                parsed_shift_time = datetime.strptime(shift_time_filter, '%H:%M').time()
                driver_trips = driver_trips.filter(shift_time=parsed_shift_time)
            except ValueError:
                pass

        if date_range:
            try:
                start_date, end_date = date_range.split(' - ')
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                driver_trips = driver_trips.filter(date__range=(start_date, end_date))
            except ValueError:
                return HttpResponse("Invalid date range format", status=400)

        order_column_index = int(request.GET.get('order[0][column]', 8))  # Order by date as default
        order_direction = request.GET.get('order[0][dir]', 'asc')
        orderable_fields = ['driver__staff_id', 'driver__driver_name', 'duty_card__duty_card_no', 'route_name', 'pick_up_time', 'drop_off_time', 'shift_time', 'trip_type', 'date', 'head_count']
        order_column = orderable_fields[order_column_index]
        if order_direction == 'desc':
            order_column = f'-{order_column}'
        driver_trips = driver_trips.order_by(order_column)

        paginator = Paginator(driver_trips, length)
        page_obj = paginator.get_page((start // length) + 1)

        data = [{
            'staff_id': trip.driver.staff_id,
            'driver_name': trip.driver.driver_name,
            'duty_card_no': trip.duty_card.duty_card_no,
            'route_name': trip.route_name,
            'pick_up_time': trip.pick_up_time.strftime('%H:%M') if trip.pick_up_time else '',
            'drop_off_time': trip.drop_off_time.strftime('%H:%M') if trip.drop_off_time else '',
            'shift_time': trip.shift_time.strftime('%H:%M') if trip.shift_time else '',
            'trip_type': trip.trip_type,
            'date': trip.date.strftime('%Y-%m-%d'),
            'head_count': trip.head_count
        } for trip in page_obj]

        return JsonResponse({
            'draw': draw,
            'recordsTotal': driver_trips.count(),
            'recordsFiltered': driver_trips.count(),
            'data': data,
        })

    context = {
        'title': 'Driver Trip Report',
    }
    return render(request, 'duty/report_data.html', context)


def download_report(request):
    """Handle downloading the report as an Excel file."""
    date_range = request.GET.get('daterange')
    route_filter = request.GET.get('route')
    shift_time_filter = request.GET.get('shift_time')
    trip_type_filter = request.GET.get('trip_type')

    driver_trips = DriverTrip.objects.all()

    # Process date range filter
    if date_range:
        try:
            start_date, end_date = date_range.split(' - ')
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            driver_trips = driver_trips.filter(date__range=(start_date, end_date))
        except ValueError:
            return HttpResponse("Invalid date range format", status=400)

    # Apply route, shift time, and trip type filters
    if route_filter:
        driver_trips = driver_trips.filter(route_name=route_filter)
    if shift_time_filter:
        driver_trips = driver_trips.filter(shift_time=shift_time_filter)
    if trip_type_filter:
        driver_trips = driver_trips.filter(trip_type=trip_type_filter)

    # Prepare the data for export
    data = [{
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
    } for trip in driver_trips]

    # Create DataFrame for Excel export
    df = pd.DataFrame(data)

    # Prepare the HTTP response for Excel download
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=driver_trip_report_{date_range}.xlsx'

    # Write the data to the Excel file using pandas
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
            trip_details.append(trip_info)

        return JsonResponse({'trips': trip_details}, safe=False)

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

        try:
            # Check if the term is in "HH:MM" format
            parsed_time = datetime.strptime(shift_time_term, "%H:%M").time()
            qs = DriverTrip.objects.filter(shift_time__startswith=parsed_time)
            shift_times = list(qs.values_list('shift_time', flat=True).distinct())
            shift_times = [time.strftime("%H:%M") for time in shift_times]
        except ValueError:
            shift_times = []

        return JsonResponse(shift_times, safe=False)
    
    return JsonResponse([], safe=False)


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            logger.debug("Form is valid, saving user.")
            user = form.save()
            messages.success(request, 'Your account has been created successfully! Please log in.')
            return redirect('login')  # Redirect to the login page
        else:
            messages.error(request, 'There were errors in your form. Please fix them.')
            logger.warning("Form is not valid.")
    else:
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
    """Returns staff load data based on filters like date, shift time, and type."""
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
    """Returns duty card submission data as a JSON response."""
    date_filter = request.GET.get('date', datetime.today().strftime('%Y-%m-%d'))

    if request.GET.get('download') == 'xlsx':
        return download_duty_card_data_as_excel(date_filter)

    date_filter_start = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.min.time()))
    date_filter_end = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.max.time()))

    duty_card_trips = DutyCardTrip.objects.values('duty_card_no').distinct()
    total_duty_cards = duty_card_trips.count()

    submitted_duty_cards = DriverTrip.objects.filter(date__range=(date_filter_start, date_filter_end)).values('duty_card').distinct()
    submitted_cards = submitted_duty_cards.count()

    pending_cards = total_duty_cards - submitted_cards if total_duty_cards > submitted_cards else 0

    data = {
        'total_duty_cards': total_duty_cards,
        'submitted_cards': submitted_cards,
        'pending_cards': pending_cards,
    }

    return JsonResponse(data)


def download_duty_card_data_as_excel(date_filter):
    """Download duty card data as an Excel file."""
    date_filter_start = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.min.time()))
    date_filter_end = timezone.make_aware(datetime.combine(datetime.strptime(date_filter, '%Y-%m-%d'), datetime.max.time()))

    duty_card_trips = DutyCardTrip.objects.values('duty_card_no').distinct()
    submitted_duty_cards = DriverTrip.objects.filter(date__range=(date_filter_start, date_filter_end)).values('duty_card__duty_card_no').distinct()

    data = []
    for duty_card in duty_card_trips:
        duty_card_no = duty_card['duty_card_no']
        is_submitted = submitted_duty_cards.filter(duty_card__duty_card_no=duty_card_no).exists()

        data.append({
            'Duty Card No': duty_card_no,
            'Submission Status': 'Submitted' if is_submitted else 'Pending',
            'Date': date_filter
        })

    df = pd.DataFrame(data)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=duty_card_details_{date_filter}.xlsx'

    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Duty Cards', index=False)

    return response


@login_required
def admin_dashboard(request):
    """Render the admin dashboard."""
    return render(request, 'duty/admin_dashboard.html')

logger = logging.getLogger(__name__)

def add_reports(request):
    """Handles adding multiple delay reports."""
    # Create a formset for multiple delay forms
    DelayDataFormSet = formset_factory(DelayDataForm, extra=1)

    if request.method == 'POST':
        logger.info("Processing the POST request")

        # Bind the form data to the formset
        formset = DelayDataFormSet(request.POST)

        if formset.is_valid():
            logger.info("All delay forms are valid, saving data")
            for form in formset:
                form.save()  # Save each form
            return redirect('success')
        else:
            # If any form is not valid, print the errors for debugging
            for form in formset:
                logger.error(f"Form validation failed: {form.errors}")

    # Handle GET request, initialize an empty formset
    else:
        formset = DelayDataFormSet()

    # Render the formset
    return render(request, 'duty/Ekg_report.html', {
        'formset': formset
    })

logger = logging.getLogger(__name__)

from django.db import IntegrityError

from django.db import IntegrityError

def add_delay_report(request):
    logger.info("add_delay_report view called")

    # Create a formset for multiple delay forms
    DelayDataFormSet = formset_factory(DelayDataForm, extra=1)

    if request.method == 'POST':
        logger.info("POST request detected")
    
        formset = DelayDataFormSet(request.POST)

        if formset.is_valid():
            logger.info("All delay forms are valid")

            # Loop through each form in the formset and process
            delay_entries = []
            for form in formset:
                # Extract the form data
                date = form.cleaned_data.get('date')
                route = form.cleaned_data.get('route')
                in_out = form.cleaned_data.get('in_out')
                std = form.cleaned_data.get('std')
                atd = form.cleaned_data.get('atd')
                sta = form.cleaned_data.get('sta')
                ata = form.cleaned_data.get('ata')
                staff_count = form.cleaned_data.get('staff_count')
                remarks = form.cleaned_data.get('remarks')

                # Check for missing required fields before saving
                if std is None or atd is None or sta is None or ata is None:
                    logger.error("Missing required field: std, atd, sta, or ata")
                    return JsonResponse({'status': 'error', 'message': 'Required fields are missing'})

                # Check if date is None and log a warning or assign a default value
                if date is None:
                    logger.warning("Date is missing in form data. Using today's date as fallback.")
                    date = datetime.today()

                # Calculate delay as a timedelta and then convert to time (HH:MM:SS)
                if sta and ata:
                    sta_time = datetime.combine(datetime.today(), sta)
                    ata_time = datetime.combine(datetime.today(), ata)
                    delay = ata_time - sta_time  # Result is timedelta
                    delay_seconds = int(delay.total_seconds())
                    delay_hours, remainder = divmod(delay_seconds, 3600)
                    delay_minutes, _ = divmod(remainder, 60)

                    # Convert to time object (HH:MM:SS)
                    delay_time = time(hour=int(delay_hours), minute=int(delay_minutes))
                    logger.info(f"Calculated delay: {delay_time}")
                else:
                    delay_time = time(0, 0, 0)  # Default to 00:00:00 if STA or ATA is missing
                    logger.warning("STA or ATA is missing; delay set to 00:00:00")

                # Save form data with delay as a time object
                try:
                    delay_instance = form.save(commit=False)
                    delay_instance.delay = delay_time
                    delay_instance.save()

                    # Collect details for email
                    delay_entries.append({
                        'date': date.strftime('%Y-%m-%d'),  # Ensure the date is not None here
                        'route': route,
                        'in_out': in_out,
                        'std': std.strftime('%H:%M'),
                        'atd': atd.strftime('%H:%M'),
                        'sta': sta.strftime('%H:%M') if sta else 'N/A',
                        'ata': ata.strftime('%H:%M') if ata else 'N/A',
                        'delay': delay_time,
                        'staff_count': staff_count,
                        'remarks': remarks,
                    })

                except IntegrityError as e:
                    logger.error(f"Database error occurred: {str(e)}")
                    return JsonResponse({'status': 'error', 'message': 'Database error occurred while saving the delay report'})

            # Handle email broadcasting if the broadcast button was clicked
            if 'broadcast' in request.POST:
                logger.info("Broadcast button clicked")
                try:
                    subject = f"Delay {route}, {sta.strftime('%H:%M')} Shift" if sta else f"Delay {route}, Unknown Shift Time"
                    message = """
                    <html>
                    <body>
                    <p>Dear Team,</p>
                    <p>Please see the delay details below:</p>
                    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 14px; text-align: center; border-color: #ddd;">
                        <thead>
                            <tr style="background-color: #f2f2f2; font-weight: bold;">
                                <th style="width: 10%;">DATE</th>
                                <th style="width: 10%;">ROUTE</th>
                                <th style="width: 10%;">IN/OUT</th>
                                <th style="width: 10%;">STD</th>
                                <th style="width: 10%;">ATD</th>
                                <th style="width: 10%;">STA</th>
                                <th style="width: 10%;">ATA</th>
                                <th style="width: 10%;">DELAY (HH:MM:SS)</th>
                                <th style="width: 10%;">STAFF COUNT</th>
                                <th style="min-width: 200px; max-width: 400px; word-wrap: break-word;">REMARKS</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    for entry in delay_entries:
                        message += f"""
                            <tr>
                                <td>{entry['date']}</td>
                                <td>{entry['route']}</td>
                                <td>{entry['in_out']}</td>
                                <td>{entry['std']}</td>
                                <td>{entry['atd']}</td>
                                <td>{entry['sta']}</td>
                                <td>{entry['ata']}</td>
                                <td>{entry['delay']}</td>
                                <td>{entry['staff_count']}</td>
                                <td>{entry['remarks']}</td>
                            </tr>
                        """
                    message += """
                        </tbody>
                    </table>
                    <br>
                    <p>Regards,<br>Sarun</p>
                    </body>
                    </html>
                    """

                    send_mail(subject=subject, message='', from_email='occekg@gmail.com', recipient_list=['sarun.ts@et.ae'], html_message=message)
                    logger.info("Email sent successfully")
                    return JsonResponse({'status': 'success', 'message': 'The delay email has been broadcast successfully.'})

                except Exception as e:
                    logger.error(f"Failed to send email: {str(e)}")
                    return JsonResponse({'status': 'error', 'message': f"Failed to send email: {str(e)}"})
            else:
                return JsonResponse({'status': 'error', 'message': 'Broadcast option not selected.'})

        else:
            logger.error("Formset validation failed")
            return JsonResponse({'status': 'error', 'message': 'Invalid form data. Please correct the errors.', 'errors': formset.errors})


