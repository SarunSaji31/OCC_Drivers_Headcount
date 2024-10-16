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
from django.db import IntegrityError
import logging
from functools import wraps
from django.conf import settings
from datetime import datetime,time
from .forms import BreakdownReportForm 
from docx import Document
from io import BytesIO
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


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
    """Custom decorator to deny access to users in DriverImportLog."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if DriverImportLog.objects.filter(staff_id=request.user.username).exists():
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
@user_in_driverimportlog_required
def admin_dashboard(request):
    """Render the admin dashboard."""
    return render(request, 'duty/admin_dashboard.html')

logger = logging.getLogger(__name__)
@login_required
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
    return render(request, 'duty/ekg_report.html', {
        'formset': formset
    })
@login_required
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
            total_valid_forms = 0  # To count how many forms are processed
            for i, form in enumerate(formset):
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

                # Skip forms missing essential fields
                if not route or not std or not atd or not sta or not ata:
                    logger.warning(f"Form {i + 1} is missing required fields. Skipping this form.")
                    continue  # Skip the current form and move to the next

                # Count the valid form
                total_valid_forms += 1

                # Check if date is None and log a warning or assign a default value
                if date is None:
                    logger.warning(f"Date is missing in form {i + 1}. Using today's date as fallback.")
                    date = timezone.now().date()

                # Calculate delay as a timedelta and then convert to time (HH:MM:SS)
                if sta and ata:
                    sta_time = datetime.combine(date, sta)
                    ata_time = datetime.combine(date, ata)
                    delay = ata_time - sta_time  # Result is timedelta
                    delay_seconds = int(delay.total_seconds())
                    delay_hours, remainder = divmod(delay_seconds, 3600)
                    delay_minutes, _ = divmod(remainder, 60)

                    # Convert to time object (HH:MM:SS)
                    delay_time = time(hour=int(delay_hours), minute=int(delay_minutes))
                    logger.info(f"Calculated delay for form {i + 1}: {delay_time}")
                else:
                    delay_time = time(0, 0, 0)  # Default to 00:00:00 if STA or ATA is missing
                    logger.warning(f"STA or ATA is missing in form {i + 1}; delay set to 00:00:00")

                # Save form data with delay as a time object
                try:
                    delay_instance = form.save(commit=False)
                    delay_instance.delay = delay_time
                    delay_instance.save()

                    # Collect details for email
                    delay_entries.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'route': route,
                        'in_out': in_out,
                        'std': std.strftime('%H:%M'),
                        'atd': atd.strftime('%H:%M'),
                        'sta': sta.strftime('%H:%M') if sta else 'N/A',
                        'ata': ata.strftime('%H:%M') if ata else 'N/A',
                        'delay': delay_time.strftime('%H:%M:%S'),
                        'staff_count': staff_count,
                        'remarks': remarks,
                    })

                except IntegrityError as e:
                    logger.error(f"Database error occurred while saving form {i + 1}: {str(e)}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Database error occurred while saving form {i + 1}: {str(e)}"
                    })

            # Check if no valid forms were submitted
            if total_valid_forms == 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No valid forms submitted. Please provide valid delay data.'
                })
            

            # Handle email broadcasting if the broadcast button was clicked
            if 'broadcast' in request.POST:
                logger.info("Broadcast button clicked")
                try:
                    # Set the subject based on the number of forms submitted
                    if total_valid_forms == 1:
                        subject = f"Delay {route}, {sta.strftime('%H:%M')} Shift" if sta else f"Delay {route}, Unknown Shift Time"
                    else:
                        subject = "Delay updates"

                    # Prepare email message
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

                    # Send the email
                    send_mail(subject=subject, message='', from_email='occekg@gmail.com', recipient_list=['sarun.ts@et.ae'], html_message=message)
                    logger.info("Email sent successfully")
                    return JsonResponse({'status': 'success', 'message': 'The delay email has been broadcast successfully.'})

                except Exception as e:
                    logger.error(f"Failed to send email: {str(e)}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Failed to send email: {str(e)}"
                    })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Broadcast option not selected.'
                })

        else:
            logger.error("Formset validation failed")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data. Please correct the errors.',
                'errors': formset.errors
            })

# Define the subcategory selection view
def subcategory_selection(request):
    return render(request, 'duty/subcategory_selection.html')


logger = logging.getLogger(__name__)

# View for EKG Breakdown Report Submission
def ekg_breakdown(request):
   if request.method == 'POST':
       form = BreakdownReportForm(request.POST)
       if form.is_valid():
           # Save the form data
           breakdown_report = form.save()
           # Log success
           logger.info("Breakdown Report submitted successfully.")
           
           # Optionally trigger email sending
           if request.POST.get('broadcast', False):
               return send_breakdown_report_email(breakdown_report)

           # Return success response
           return JsonResponse({'status': 'success', 'message': 'Breakdown Report submitted successfully.'})
       
       else:
           # Log form errors
           logger.error(f"Form validation failed: {form.errors}")
           return JsonResponse({'status': 'error', 'message': 'Invalid form data. Please correct the errors.', 'errors': form.errors.as_json()})
   
   else:
       # Render the initial form for GET requests
       form = BreakdownReportForm()
       return render(request, 'duty/ekg_breakdown.html', {'form': form})

def set_cell_border(cell, **kwargs):
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()
    for edge in ('top', 'bottom', 'left', 'right'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = f"w:{edge}"
            element = OxmlElement(tag)
            element.set(qn('w:val'), edge_data.get("val", "single"))  # Normal border
            element.set(qn('w:sz'), str(edge_data.get("sz", 4)))  # Smaller size for normal border
            element.set(qn('w:space'), str(edge_data.get("space", 0)))
            element.set(qn('w:color'), edge_data.get("color", "000000"))
            tcPr.append(element)

def send_breakdown_report_email(breakdown_report):
    try:
        # Create the Word document
        document = Document()

        # Set document margins (in cm)
        sections = document.sections
        for section in sections:
            section.top_margin = Pt(1.13 * 28.35)    # Convert cm to points
            section.left_margin = Pt(1.41 * 28.35)
            section.bottom_margin = Pt(0 * 28.35)
            section.right_margin = Pt(2.54 * 28.35)

        # Set the document default font to Calibri, size 10
        style = document.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(10)

        # Add centered title with size 16, bold, black
        title = document.add_paragraph()
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER  # Center alignment
        run = title.add_run('Breakdown Report')
        run.font.size = Pt(16)
        run.font.bold = True

        # Section A: To be completed by the Provider
        document.add_paragraph()  # Add spacing between title and table
        section_heading = document.add_paragraph()
        section_heading.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER  # Center alignment
        run = section_heading.add_run('Section A: To be completed by the Provider')
        run.font.size = Pt(10)
        run.font.bold = True

        # Create the main table (for both Section A and Section B)
        table = document.add_table(rows=0, cols=2)
        table.autofit = True
        table.style = 'Table Grid'

        # Adding Section A fields to the table
        section_a_rows = [
            ('Date and Time of Report', breakdown_report.reported_datetime),
            ('Breakdown Date and Time', breakdown_report.breakdown_datetime),
            ('Breakdown Location', breakdown_report.location),
            ('Route #', breakdown_report.route_number),
            ('Trip Work Order #', breakdown_report.trip_work_order),
            ('No. of passengers involved', breakdown_report.passengers_involved),
            ('EK Staff numbers', breakdown_report.ek_staff_numbers),
            ('Non-EK Passenger Details', breakdown_report.non_ek_passenger_details),
            ('No. of injured passengers', breakdown_report.injured_passengers),
            ('Action taken for injured passengers', breakdown_report.action_taken_for_injured),
            ('Damage to the vehicle(s)', breakdown_report.vehicle_damage),
            ('Driver Name and ID No.', f"{breakdown_report.driver_name} (ID: {breakdown_report.driver_id})"),
            ('Driver Shift', breakdown_report.driver_shift),
            ('Description of the Breakdown', breakdown_report.breakdown_description),
            ('No. of EK vehicles involved', breakdown_report.ek_vehicles_involved),
            ('Vehicle Make and Plate #', breakdown_report.vehicle_make_plate),
            ('Replacement vehicle #', breakdown_report.replacement_vehicle),
            ('Reported to person at EK', breakdown_report.reported_to_person),
            ('Reported Date and Time', breakdown_report.reported_datetime)
        ]

        # Add Section A rows with normal borders
        for label, value in section_a_rows:
            row = table.add_row()
            row.cells[0].text = label
            row.cells[1].text = str(value)
            for cell in row.cells:
                set_cell_border(cell, top={"sz": 4, "val": "single", "color": "000000"},
                                     bottom={"sz": 4, "val": "single", "color": "000000"},
                                     left={"sz": 4, "val": "single", "color": "000000"},
                                     right={"sz": 4, "val": "single", "color": "000000"})

        # Section B: To be completed by EK Transport Services (in same table)
        row = table.add_row()
        row.cells[0].merge(row.cells[1])  # Merge both cells to span the row
        row.cells[0].text = "Section B: To be completed by EK Transport Services"
        row.cells[0].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        run = row.cells[0].paragraphs[0].runs[0]
        run.font.size = Pt(10)
        run.font.bold = True

        # Adding Section B fields to the table
        section_b_rows = [
            ('Incident Reference Number', ''),
            ('If there are injuries, has the passenger been spoken to?', ''),
            ('Have all attachments been added to the case?', '')
        ]

        # Add Section B rows
        for label, value in section_b_rows:
            row = table.add_row()
            row.cells[0].text = label
            row.cells[1].text = value
            for cell in row.cells:
                set_cell_border(cell, top={"sz": 4, "val": "single", "color": "000000"},
                                     bottom={"sz": 4, "val": "single", "color": "000000"},
                                     left={"sz": 4, "val": "single", "color": "000000"},
                                     right={"sz": 4, "val": "single", "color": "000000"})

        # Save the document to memory
        report_buffer = BytesIO()
        document.save(report_buffer)
        report_buffer.seek(0)

        # Prepare email content
        subject = "Breakdown Report"
        email_body = render_to_string('duty/breakdown_report_email.html', {'report': breakdown_report})

        # Prepare email with attachment
        email = EmailMessage(
            subject=subject,
            body=email_body,
            from_email='occekg@gmail.com',
            to=['sarun.ts@et.ae']  # Update with recipient list
        )
        email.attach('Breakdown_Report.docx', report_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        email.content_subtype = 'html'

        # Send the email
        email.send()

        logger.info("Breakdown report email sent successfully.")
        return JsonResponse({'status': 'success', 'message': 'Breakdown email broadcast successfully.'})

    except Exception as e:
        logger.error(f"Failed to send breakdown report email: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f"Failed to send breakdown report email: {str(e)}"})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
