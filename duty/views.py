from functools import wraps
import os
import logging

# Third-Party Imports
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
import pdfkit

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now
from django.utils import timezone

# Project-Specific Imports
from .decorators import user_in_driverimportlog_required
from .forms import (
    DelayDataForm, DriverTripFormSet, CustomUserCreationForm,
    PasswordResetRequestForm, SetNewPasswordForm, formset_factory,
    BreakdownReportForm
)
from .models import (
    DriverTrip, DriverImportLog, DutyCardTrip, DelayData,
    BreakdownReport, StmRoute, StmPickupPoint, StmShiftTime
)


# Setup logger
logger = logging.getLogger(__name__)

@login_required
def home(request):
    """Render the home page for logged-in users with driver trip details."""
    staff_id = request.user.username
    staff_name = DriverImportLog.objects.filter(staff_id=staff_id).values_list('driver_name', flat=True).first() or staff_id

    # Fetch driver trips
    driver_trips = DriverTrip.objects.filter(driver__staff_id=staff_id).select_related('duty_card')
    driver_trip_data = [{
        'route_name': trip.route_name,
        'pick_up_time': trip.pick_up_time.strftime('%H:%M:%S'),
        'drop_off_time': trip.drop_off_time.strftime('%H:%M:%S'),
        'shift_time': trip.shift_time.strftime('%H:%M:%S'),
        'head_count': trip.head_count,
        'trip_type': trip.trip_type,
        'date': trip.date.strftime('%Y-%m-%d'),
        'capacity': trip.duty_card.capacity  # Include capacity from the related DutyCardTrip
    } for trip in driver_trips]

    context = {
        'staff_name': staff_name,
        'driver_trips': driver_trip_data,
    }
    return render(request, 'duty/home.html', context)

@login_required
def submission_history(request):
    """Display a summary of the submission history of the logged-in user."""
    staff_id = request.user.username
    driver = DriverImportLog.objects.filter(staff_id=staff_id).first()

    if not driver:
        return render(request, 'duty/user_submission_history.html', {
            'error_message': "No submission history found for this user."
        })

    # Group submissions by date and duty card number
    submissions = DriverTrip.objects.filter(driver=driver).order_by('-date')
    submission_summary = {}
    for trip in submissions:
        key = (trip.date, trip.duty_card.duty_card_no)
        if key not in submission_summary:
            submission_summary[key] = []
        submission_summary[key].append(trip)

    context = {
        'staff_name': driver.driver_name,
        'submission_summary': submission_summary,
    }

    return render(request, 'duty/user_submission_history.html', context)

@login_required
def enter_head_count(request):
    """
    Handle the form for entering headcount details.
    Display success message on the same page without redirection.
    """
    staff_id = request.user.username
    driver = DriverImportLog.objects.filter(staff_id=staff_id).first()

    if not driver:
        return render(request, 'duty/enter_head_count.html', {
            'error_message': "Driver information not found. Please contact support."
        })

    staff_name = driver.driver_name or staff_id
    success_message = None  # To hold the success message

    if request.method == 'POST':
        trip_formset = DriverTripFormSet(request.POST, prefix='drivertrip_set')
        duty_card_no = request.POST.get('duty_card_no')

        if not duty_card_no:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Please fill in the Duty Card No."
            })

        duty_card = DutyCardTrip.objects.filter(duty_card_no=duty_card_no).first()
        if not duty_card:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Invalid Duty Card No. Please check and try again."
            })

        try:
            desired_date_str = request.POST.get('drivertrip_set-0-date')
            if not desired_date_str:
                raise ValueError("Date field is missing or empty.")
            desired_date = datetime.strptime(desired_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Invalid date format. Please use YYYY-MM-DD."
            })

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
            success_message = "The headcount has been successfully saved."  # Set success message
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
        'success_message': success_message,  # Pass success message to template
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

from django.http import JsonResponse
from datetime import datetime,date
from .models import DutyCardTrip  # Ensure this imports your model correctly


def get_duty_card_details(request):
    """
    Fetch details of a duty card, including trips and links to route details.
    """
    if 'duty_card_no' in request.GET:
        duty_card_no = request.GET.get('duty_card_no')

        # Fetch trips from the database and order by pick_up_time
        trips = DutyCardTrip.objects.filter(duty_card_no=duty_card_no).order_by('pick_up_time')

        if not trips.exists():
            return JsonResponse({'error': 'No trips found for the provided duty card number.'}, status=404)

        trip_details = []
        for trip in trips:
            # Normalize the trip_type field
            normalized_trip_type = 'inbound' if trip.trip_type and trip.trip_type.lower() in ['in', 'inbound'] else 'outbound'

            # Prepare trip details for the response
            trip_info = {
                'route_name': trip.route_name,
                'pick_up_time': trip.pick_up_time.strftime("%H:%M") if trip.pick_up_time else '',
                'drop_off_time': trip.drop_off_time.strftime("%H:%M") if trip.drop_off_time else '',
                'shift_time': trip.shift_time.strftime("%H:%M") if trip.shift_time else '',
                'trip_type': normalized_trip_type,
                'date': trip.date.strftime("%Y-%m-%d") if hasattr(trip, 'date') else datetime.today().strftime("%Y-%m-%d"),
                'head_count': trip.head_count if hasattr(trip, 'head_count') else 0,
                # Generate a dynamic link to route details
                'details_link': f"/route-details/?route={trip.route_name}&shift_time={trip.shift_time.strftime('%H:%M') if trip.shift_time else ''}&type={normalized_trip_type}"
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
    DelayDataFormSet = formset_factory(DelayDataForm, extra=1)

    if request.method == 'POST':
        logger.info("Processing POST request")
        formset = DelayDataFormSet(request.POST)

        if formset.is_valid():
            try:
                with transaction.atomic():
                    for form in formset:
                        if form.cleaned_data:  # Skip empty forms
                            logger.info(f"Saving form with data: {form.cleaned_data}")
                            form.save()
                    return JsonResponse({'status': 'success', 'message': 'Forms saved successfully!'})
            except Exception as e:
                logger.error(f"Error saving forms: {e}")
                return JsonResponse({'status': 'error', 'message': 'An error occurred while saving the forms.'})
        else:
            logger.error(f"Formset validation failed: {formset.errors}")
            return JsonResponse({'status': 'error', 'message': 'Invalid form data.', 'errors': formset.errors})

    formset = DelayDataFormSet()
    return render(request, 'duty/Ekg_report.html', {'formset': formset})



from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db import transaction
from django.forms import formset_factory
from django.contrib.auth.decorators import login_required
from .forms import DelayDataForm

@login_required
def add_delay_report(request):
    """Handles adding and validating delay reports with AJAX responses."""
    DelayDataFormSet = formset_factory(DelayDataForm, extra=1)

    if request.method == 'POST':
        formset = DelayDataFormSet(request.POST)
        total_valid_forms = 0
        error_messages = []

        if formset.is_valid():
            try:
                with transaction.atomic():
                    for i, form in enumerate(formset):
                        try:
                            instance = form.save(commit=False)
                            date = form.cleaned_data.get('date')
                            sta = form.cleaned_data.get('sta')
                            ata = form.cleaned_data.get('ata')

                            if date and sta and ata:
                                # Calculate delay as a timedelta
                                delay_timedelta = datetime.combine(date, ata) - datetime.combine(date, sta)
                                if delay_timedelta.total_seconds() >= 0:  # Ensure delay is not negative
                                    instance.delay = (datetime.min + delay_timedelta).time()  # Store as time
                                else:
                                    instance.delay = None  # Set delay to None if ATA < STA

                            # Save the instance to the database
                            instance.save()
                            total_valid_forms += 1
                        except Exception as e:
                            error_messages.append(f"Form {i + 1}: {str(e)}")

                if total_valid_forms == 0:
                    return JsonResponse({'status': 'error', 'message': 'No valid forms submitted.'})

                return JsonResponse({'status': 'success', 'message': f'{total_valid_forms} form(s) processed successfully.'})

            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

        # Handle invalid forms
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid form data.',
            'errors': formset.errors,
        })

    formset = DelayDataFormSet()
    return render(request, 'duty/add_delay_report.html', {'formset': formset})

@login_required
@user_in_driverimportlog_required
# Define the subcategory selection view
def subcategory_selection(request):
    return render(request, 'duty/subcategory_selection.html')


logger = logging.getLogger(__name__)

@login_required
def ekg_breakdown(request):
    """Handles submission of EKG Breakdown Report."""
    if request.method == 'POST':
        form = BreakdownReportForm(request.POST)
        if form.is_valid():
            # Save the form data
            breakdown_report = form.save()
            # Log success
            logger.info("Breakdown Report submitted successfully.")

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

@login_required
def stm_dashboard(request):
    """
    Renders the STM dashboard.
    """
    return render(request, 'duty/STM_dashboard.html')


logger = logging.getLogger(__name__)

from django.utils.timezone import localdate

def fleet_counts_api(request):
    today = localdate()
    month_start = today.replace(day=1)

    daily_delay_count = DelayData.objects.filter(date=today).count()
    monthly_delay_count = DelayData.objects.filter(date__gte=month_start).count()

    daily_breakdown_count = BreakdownReport.objects.filter(breakdown_datetime__date=today).count()
    monthly_breakdown_count = BreakdownReport.objects.filter(breakdown_datetime__date__gte=month_start).count()

    total_delay_count = DelayData.objects.all().count()
    total_breakdown_count = BreakdownReport.objects.all().count()

    data = {
        'daily_delay_count': daily_delay_count,
        'monthly_delay_count': monthly_delay_count,
        'daily_breakdown_count': daily_breakdown_count,
        'monthly_breakdown_count': monthly_breakdown_count,
        'total_delay_count': total_delay_count,
        'total_breakdown_count': total_breakdown_count,
    }

    return JsonResponse(data)


logger = logging.getLogger(__name__)

def download_fleet_report(request):
    """
    Function to download fleet delay or breakdown reports as XLSX.
    """
    # Get request parameters
    report_type = request.GET.get('report_type')  # daily, monthly, or total
    report_category = request.GET.get('report_category')  # delay or breakdown

    # Log the parameters to check if they are coming through correctly
    logger.info(f"Received report_type: {report_type}, report_category: {report_category}")

    # Check if report_type or report_category is missing
    if not report_type or not report_category:
        logger.error('Invalid report type or category.')
        return JsonResponse({'status': 'error', 'message': 'Invalid report type or category.'})

    # Define the query based on the report type
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    queryset = None  # Initialize queryset

    if report_type == 'daily':
        if report_category == 'delay':
            queryset = DelayData.objects.filter(date=today)
        elif report_category == 'breakdown':
            queryset = BreakdownReport.objects.filter(breakdown_datetime__date=today)
    elif report_type == 'monthly':
        if report_category == 'delay':
            queryset = DelayData.objects.filter(date__gte=month_start)
        elif report_category == 'breakdown':
            queryset = BreakdownReport.objects.filter(breakdown_datetime__date__gte=month_start)
    elif report_type == 'total':
        if report_category == 'delay':
            queryset = DelayData.objects.all()
        elif report_category == 'breakdown':
            queryset = BreakdownReport.objects.all()

    # Check if the queryset is empty
    if queryset is None or not queryset.exists():
        logger.error('No data available for the selected report.')
        return JsonResponse({'status': 'error', 'message': 'No data available for the selected report.'})

    # Create an Excel workbook
    workbook = Workbook()
    worksheet = workbook.active

    # Define headers for the Excel sheet
    if report_category == 'delay':
        headers = ['Date', 'Route', 'In/Out', 'STD', 'STA', 'ATD', 'ATA', 'Delay', 'Remarks', 'Staff Count']
        worksheet.append(headers)
        # Add data to Excel rows
        for delay in queryset:
            worksheet.append([
                delay.date, 
                delay.route,  
                delay.in_out,  
                delay.std.strftime('%H:%M') if delay.std else None,  
                delay.sta.strftime('%H:%M') if delay.sta else None, 
                delay.atd.strftime('%H:%M') if delay.atd else None,  
                delay.ata.strftime('%H:%M') if delay.ata else None,
                delay.delay,  
                delay.remarks, 
                delay.staff_count
            ])

    elif report_category == 'breakdown':
        headers = ['Report Date', 'Breakdown Date', 'Location', 'Route #', 'Trip Work Order', 'Passengers Involved', 
                   'EK Staff Numbers', 'Non-EK Passenger Details', 'Injured Passengers', 'Action Taken for Injured',
                   'Vehicle Damage', 'Driver Name', 'Driver ID', 'Driver Shift', 'Breakdown Description', 
                   'EK Vehicles Involved', 'Vehicle Make and Plate', 'Replacement Vehicle', 'Reported To', 'Reported Date']
        worksheet.append(headers)
        # Add data to Excel rows
        for breakdown in queryset:
            worksheet.append([
                breakdown.reported_datetime.strftime('%Y-%m-%d %H:%M'),
                breakdown.breakdown_datetime.strftime('%Y-%m-%d %H:%M'),
                breakdown.location,
                breakdown.route_number,
                breakdown.trip_work_order,
                breakdown.passengers_involved,
                breakdown.ek_staff_numbers,
                breakdown.non_ek_passenger_details,
                breakdown.injured_passengers,
                breakdown.action_taken_for_injured,
                breakdown.vehicle_damage,
                breakdown.driver_name,
                breakdown.driver_id,
                breakdown.driver_shift,
                breakdown.breakdown_description,
                breakdown.ek_vehicles_involved,
                breakdown.vehicle_make_plate,
                breakdown.replacement_vehicle,
                breakdown.reported_to_person,
                breakdown.reported_datetime.strftime('%Y-%m-%d %H:%M')
            ])

    # Prepare the response as an XLSX file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{report_category}_{report_type}_report.xlsx"'
    
    # Save workbook to the response
    workbook.save(response)
    
    return response

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from .models import StmRoute


def ajax_search_route(request):
    if request.method == 'GET':
        # Retrieve filter inputs
        route_code = request.GET.get('route', '').strip()
        route_name = request.GET.get('route_name', '').strip()
        route_type = request.GET.get('type', '').strip()
        work_hub = request.GET.get('work_hub', '').strip()
        pick_up_point = request.GET.get('pick_up_point', '').strip()
        stop_id = request.GET.get('stop_id', '').strip()
        shift_time = request.GET.get('shift_time', '').strip()
        connection_from = request.GET.get('connection_from', '').strip()
        connection_to = request.GET.get('connection_to', '').strip()

        # Construct query with partial matching for the main route table
        query = Q()
        if route_code:
            query &= Q(route__icontains=route_code)
        if route_name:
            query &= Q(route__icontains=route_name)
        if route_type:
            query &= Q(route_type__icontains=route_type)
        if work_hub:
            query &= Q(work_hub__icontains=work_hub)
        if connection_from:
            query &= Q(connection_from__icontains=connection_from)
        if connection_to:
            query &= Q(connection_to__icontains=connection_to)

        # Retrieve filtered routes
        routes = StmRoute.objects.filter(query).distinct()

        route_data = []
        seen_entries = set()

        for route in routes:
            # Filter related tables based on optional parameters
            pickup_points = (
                route.pickup_points.filter(pick_up_point__icontains=pick_up_point)
                if pick_up_point else route.pickup_points.all()
            )
            if stop_id:
                pickup_points = pickup_points.filter(stop_id__icontains=stop_id)

            shift_times = (
                route.shift_times.filter(shift_time__icontains=shift_time)
                if shift_time else route.shift_times.all()
            )

            # Build unique route data for JSON response only if related data matches
            if pickup_points.exists() or not pick_up_point:
                for shift in shift_times:
                    entry_key = (route.route, route.route_type, shift.shift_time, route.work_hub)
                    if entry_key not in seen_entries:
                        seen_entries.add(entry_key)
                        route_data.append({
                            'route_code': route.route,
                            'route_name': route.route,
                            'route_type': route.route_type,  # Include route type
                            'work_hub': route.work_hub,
                            'connection_from': route.connection_from,
                            'connection_to': route.connection_to,
                            'shift_time': shift.shift_time.strftime('%H:%M') if shift.shift_time else '-',
                            # Generate a dynamic link including route type
                            'link': f"/route-details/?route={route.route}&shift_time={shift.shift_time.strftime('%H:%M') if shift.shift_time else ''}&type={route.route_type}"
                        })

        # Return JSON response for AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'routes': route_data})

        # If not an AJAX request, render the template with routes
        return render(request, 'duty/search_form_with_results.html', {'routes': route_data})

    # Return error page for invalid requests
    return render(request, 'duty/error_page.html', {'error': 'Invalid request'})


from datetime import datetime, time
from django.shortcuts import render
from .models import StmRoute, StmShiftTime, StmPickupPoint


def route_details(request):
    # Retrieve input parameters from the request
    route_name = request.GET.get('route')
    route_type = request.GET.get('type')  # Route Type: Optional
    shift_time = request.GET.get('shift_time')

    # Debugging: Log received parameters
    print(f"Route: {route_name}, Type: {route_type}, Shift Time: {shift_time}")

    # Validate required inputs
    if not route_name:
        return render(request, 'duty/error_page.html', {'error': 'Route is missing. Please provide a valid route.'})
    if not shift_time:
        return render(request, 'duty/error_page.html', {'error': 'Shift time is missing. Please specify a valid shift time.'})

    # If type is missing, infer it from the database
    if not route_type:
        matching_routes = StmRoute.objects.filter(route__iexact=route_name).distinct()
        if matching_routes.count() == 1:
            # Automatically set the route type if only one exists
            route_type = matching_routes.first().route_type
        else:
            return render(request, 'duty/error_page.html', {'error': 'Route type is missing and cannot be inferred. Please specify Inbound or Outbound.'})

    # Filter the route based on route_name, route_type, and shift_time
    route_qs = StmRoute.objects.filter(route__iexact=route_name, route_type__iexact=route_type)
    if not route_qs.exists():
        return render(request, 'duty/error_page.html', {'error': 'No matching route found for the specified type and shift time.'})

    route_data_list = []

    # Iterate through matching routes
    for route in route_qs:
        # Filter shift times for the route
        shift_times = StmShiftTime.objects.filter(route=route, shift_time=shift_time).order_by('stop_order')
        if not shift_times.exists():
            continue

        # Create a mapping of stop order to times
        stop_order_to_times = {
            shift.stop_order: {
                'time': shift.time if isinstance(shift.time, str) else (shift.time.strftime('%H:%M') if shift.time else '-'),
                'special_time': shift.special_time if isinstance(shift.special_time, str) else (shift.special_time.strftime('%H:%M') if shift.special_time else '-')
            }
            for shift in shift_times
        }

        # Get all pickup points for the route
        pickup_points = StmPickupPoint.objects.filter(route=route).order_by('pick_up_point_order_id')

        # Prepare route data
        route_data = {
            'route_name': route.route,
            'route_type': route.route_type,
            'operating_days_1': route.operating_days_1,
            'operating_days_2': route.operating_days_2,
            'work_hub': route.work_hub,
            'shift_time': shift_time,
            'pickup_points': [
                {
                    'stop_id': point.stop_id,
                    'pick_up_point': point.pick_up_point,
                    'time': stop_order_to_times.get(point.pick_up_point_order_id, {}).get('time', '-'),
                    'special_time': stop_order_to_times.get(point.pick_up_point_order_id, {}).get('special_time', '-')
                }
                for point in pickup_points
            ]
        }

        route_data_list.append(route_data)

    # Render the results on the timetable template
    return render(request, 'duty/stm_timetable.html', {'route_data_list': route_data_list})

def connection_from_autocomplete(request):
    if 'term' in request.GET:
        qs = StmRoute.objects.filter(connection_from__icontains=request.GET.get('term')).values_list('connection_from', flat=True).distinct()
        suggestions = list(qs)
        return JsonResponse(suggestions, safe=False)

def stm_timetables(request):
    # Get route and shift_time from the query parameters
    route_name = request.GET.get('route')
    shift_time = request.GET.get('shift_time')

    # Log the received parameters for debugging
    print(f"Received route: {route_name}, shift time: {shift_time}")

    # Validate and fetch data based on route and shift time
    if route_name and shift_time:
        # Use case-insensitive filtering for the route
        routes = StmRoute.objects.filter(route__iexact=route_name)

        if not routes.exists():
            return render(request, 'duty/stm_timetable.html', {'error': 'No matching route found.'})

        route_data_list = []
        for route in routes:
            shift = StmShiftTime.objects.filter(route=route, shift_time=shift_time).first()

            if shift:
                # Fetch pickup points for the route and order them by pick_up_point_order_id
                pickup_points = StmPickupPoint.objects.filter(route=route).order_by('pick_up_point_order_id')

                # Create a mapping of stop orders to shift times
                shift_times = StmShiftTime.objects.filter(route=route).order_by('stop_order')
                stop_order_to_time = {
                    shift.stop_order: shift.time if isinstance(shift.time, str) else (shift.time.strftime('%H:%M') if shift.time else '-')
                    for shift in shift_times
                }

                # Log the retrieved data for verification
                print(f"Route: {route}, Shift: {shift}, Number of pickup points: {len(pickup_points)}")

                route_data = {
                    'route_name': route.route,
                    'route_type': route.route_type,
                    'operating_days_1': route.operating_days_1,
                    'operating_days_2': route.operating_days_2,
                    'work_hub': route.work_hub,
                    'shift_time': shift.shift_time if isinstance(shift.shift_time, str) else (shift.shift_time.strftime('%H:%M') if shift.shift_time else 'N/A'),
                    'pickup_points': [
                        {
                            'stop_id': point.stop_id,
                            'pick_up_point': point.pick_up_point,
                            'time': stop_order_to_time.get(point.pick_up_point_order_id, '-'),
                            'special_time': shift.special_time if isinstance(shift.special_time, str) else (shift.special_time.strftime('%H:%M') if shift.special_time else '-')
                        }
                        for point in pickup_points
                    ]
                }
                route_data_list.append(route_data)

        if route_data_list:
            return render(request, 'duty/stm_timetable.html', {'route_data_list': route_data_list})
        else:
            return render(request, 'duty/stm_timetable.html', {'error': 'No matching shift time found for the selected route.'})
    else:
        print("Invalid route or shift time provided")
        return render(request, 'duty/stm_timetable.html', {'error': 'Invalid route or shift time provided'})

import os
import pandas as pd
from datetime import datetime, timedelta
from django.http import HttpResponse, FileResponse
from django.shortcuts import render
from django.conf import settings

# Directory setup
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'uploads')
DOWNLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'downloads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Specific groupings for crew count aggregation
specific_groupings = {
    "EM6 TALAL QAMZI": ["EM6", "Talal", "Al Qamzi"],
    "SARAB SAFA": ["SARAB", "SAFA"],
    "SABREEN FALTAT MANAZIL TOWER": ["SAB", "FT", "MT"],
    "SONBOULAH GARHOUD TOWERS": ["SON", "GT"],
    "TECOM DR.KHALIFA": ["TECOM", "Dr. K"],
    "MILLENIUM PINK GROSVENOR": ["MIT", "PINK", "GCT"],
    "PARK ZABEEL 7 PEARLS": ["PZABEEL", "7Pearls"],
    "DSO": ["DSO"]
}

# Name mapping for full names
name_mapping = {
    "Talal": "TALAL",
    "Al Qamzi": "QAMZI",
    "EM6": "EM6",
    "Dr. K": "DR.KHALIFA",
    "TECOM": "TECOM 1,2",
    "GCT": "GROSVENOUR",
    "PINK": "PINK",
    "SAB": "SABREEN",
    "FT": "FALTAT",
    "MT": "MANAZIL TOWER",
    "SON": "SONBOULAH",
    "GT": "GARHOUD TOWERS",
    "MIT": "MILLINUM TOWER",
    "PZABEEL": "PARK ZABEEL 1,2",
    "7Pearls": "7 PEARLS",
    "DSO": "DSO"
}

# Function to calculate "No of Units"
def calculate_units(crew_count):
    return (crew_count - 1) // 31 + 1 if crew_count > 0 else 0

# Function to process data
def process_data(df, specific_groupings, name_mapping, direction):
    grouped_data = []
    for _, row in df.iterrows():
        time = row["TIME"]
        if isinstance(time, str):
            time = datetime.strptime(time, '%H:%M').time()
        if direction == "Outbound":
            time = (datetime.combine(datetime.today(), time) + timedelta(minutes=14)).time()
        formatted_time = time.strftime('%H:%M')

        for group_name, buildings in specific_groupings.items():
            crew_count = 0
            valid_buildings = []

            # Loop through buildings in the group
            for building in buildings:
                if building in df.columns:
                    building_value = row[building]
                    if pd.notna(building_value) and building_value > 0:
                        crew_count += building_value
                        valid_buildings.append(name_mapping.get(building, building))

            # Add to grouped data if crew count > 0
            if crew_count > 0:
                grouped_data.append({
                    "DATE": (datetime.now() + timedelta(days=1)).strftime("%d-%b"),  # Updated format
                    "NO OF UNITS": calculate_units(crew_count),
                    "TIME": formatted_time,
                    "FROM": ", ".join(valid_buildings) if direction == "Inbound" else "EAC-C",
                    "TO": "EAC-C" if direction == "Inbound" else ", ".join(valid_buildings),
                    "CREW": crew_count
                })

    return pd.DataFrame(grouped_data)


# File processing function
def process_files(inbound_file, outbound_file):
    # Read inbound and outbound Excel files
    df_inbound = pd.read_excel(inbound_file)
    df_outbound = pd.read_excel(outbound_file)

    # Clean column names
    df_inbound.columns = df_inbound.columns.str.strip()
    df_outbound.columns = df_outbound.columns.str.strip()

    # Process inbound and outbound data
    df_inbound_grouped = process_data(df_inbound, specific_groupings, name_mapping, "Inbound")
    df_outbound_grouped = process_data(df_outbound, specific_groupings, name_mapping, "Outbound")

    # Reorder columns
    df_inbound_grouped = df_inbound_grouped[['DATE', 'NO OF UNITS', 'TIME', 'FROM', 'TO', 'CREW']]
    df_outbound_grouped = df_outbound_grouped[['DATE', 'NO OF UNITS', 'TIME', 'FROM', 'TO', 'CREW']]

    # Save processed files
    inbound_output_path = os.path.join(DOWNLOAD_DIR, 'Cabin_crew_inbound_trips.xlsx')
    outbound_output_path = os.path.join(DOWNLOAD_DIR, 'Cabin_crew_outbound_trips.xlsx')

    df_inbound_grouped.to_excel(inbound_output_path, index=False)
    df_outbound_grouped.to_excel(outbound_output_path, index=False)

    return inbound_output_path, outbound_output_path

# View for uploading files
def upload_view(request):
    if request.method == 'POST' and request.FILES.get('inbound_file') and request.FILES.get('outbound_file'):
        inbound_file = request.FILES['inbound_file']
        outbound_file = request.FILES['outbound_file']
        try:
            inbound_path, outbound_path = process_files(inbound_file, outbound_file)
            return render(request, 'duty/upload.html', {
                'inbound_path': f'/download/{os.path.basename(inbound_path)}',
                'outbound_path': f'/download/{os.path.basename(outbound_path)}'
            })
        except Exception as e:
            return render(request, 'duty/upload.html', {'error': str(e)})
    return render(request, 'duty/upload.html')

# View for downloading files
def download_file(request, filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
    return HttpResponse("File not found.", status=404)

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import F, ExpressionWrapper, DurationField, Count
from django.utils.timezone import now
from datetime import timedelta
from .models import DelayData

def stm_dashboard(request):
    """
    Render the STM dashboard with the most delayed trips for the current month.
    """
    start_of_month = now().replace(day=1).date()
    today = now().date()

    delayed_trips = (
        DelayData.objects.annotate(
            delay_duration=ExpressionWrapper(F('ata') - F('sta'), output_field=DurationField())
        )
        .filter(date__gte=start_of_month, date__lte=today, delay_duration__gt=timedelta(minutes=30))
        .annotate(delay_count=Count('id'))
        .values('route', 'sta', 'delay_count')
        .order_by('-delay_count')
    )

    # Convert sta to string for the template
    for trip in delayed_trips:
        trip['sta'] = str(trip['sta'])

    context = {
        'delayed_trips': delayed_trips,
    }
    return render(request, 'duty/STM_dashboard.html', context)

from datetime import datetime
from django.http import JsonResponse
from django.db.models import Count
from .models import DelayData

def get_most_delayed_trips_api(request):
    """
    Returns the top 5 most delayed trips.
    Accepts either:
      - "selected_month" in "YYYY-MM" format for full-month data, or
      - "selected_date" in "YYYY-MM-DD" format to use records from the 1st until that date.
    """
    selected_month_str = request.GET.get('selected_month')
    if selected_month_str:
        try:
            year, month = selected_month_str.split('-')
            selected_year = int(year)
            selected_month = int(month)
            selected_date = date(selected_year, selected_month, 1)
            last_day = calendar.monthrange(selected_year, selected_month)[1]
            month_start = selected_date
            month_end = date(selected_year, selected_month, last_day)
        except Exception:
            selected_date = now().date()
            month_start = selected_date.replace(day=1)
            month_end = selected_date
    else:
        selected_date_str = request.GET.get('selected_date')
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = now().date()
        else:
            selected_date = now().date()
        month_start = selected_date.replace(day=1)
        month_end = selected_date

    delayed_trips = (
        DelayData.objects.filter(date__gte=month_start, date__lte=month_end)
        .values('route', 'sta')
        .annotate(delay_count=Count('id'))
        .order_by('-delay_count')[:5]
    )

    # Convert non-serializable fields (e.g. time objects) to string.
    for trip in delayed_trips:
        trip['sta'] = str(trip['sta'])

    return JsonResponse(list(delayed_trips), safe=False)


from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db.models import ExpressionWrapper, F, DurationField
from duty.models import DelayData  # Ensure this import works after moving DelayData to the top level

def get_otp_chart_data(request):
    """
    Returns OTP data for a given period.
    Expects:
      - period: "daily", "monthly", or "yearly"
      - For monthly filtering, an optional parameter "selected_month" in "YYYY-MM" format.
      - Otherwise, "selected_date" in "YYYY-MM-DD" format.
    """
    period = request.GET.get("period", "daily").lower()
    selected_month_str = request.GET.get("selected_month")

    if selected_month_str:
        try:
            year, month = selected_month_str.split('-')
            selected_date = date(int(year), int(month), 1)
        except Exception:
            selected_date = now().date()
    else:
        selected_date_str = request.GET.get("selected_date")
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            except ValueError:
                selected_date = now().date()
        else:
            selected_date = now().date()

    qs = DelayData.objects.all()
    if period == "daily":
        qs = qs.filter(date=selected_date)
    elif period == "monthly":
        # Get the last day of the month.
        last_day = calendar.monthrange(selected_date.year, selected_date.month)[1]
        month_end = selected_date.replace(day=last_day)
        qs = qs.filter(date__gte=selected_date, date__lte=month_end)
    elif period == "yearly":
        year_start = selected_date.replace(month=1, day=1)
        qs = qs.filter(date__gte=year_start, date__lte=selected_date)
    else:
        qs = qs.filter(date=selected_date)

    qs = qs.annotate(
        delay_duration=ExpressionWrapper(F("atd") - F("std"), output_field=DurationField())
    )
    total_count = qs.count()
    failure_count = qs.filter(delay_duration__gt=timedelta(minutes=10)).count()
    on_time_count = total_count - failure_count

    data = {
        "labels": ["On Time", "Not On Time"],
        "data": [on_time_count, failure_count],
    }
    return JsonResponse(data)

from datetime import datetime, date, timedelta
import calendar
from django.http import JsonResponse
from django.db.models import Count, ExpressionWrapper, DurationField, F, Q
from django.utils.timezone import now
from .models import DelayData, BreakdownReport

def filter_dashboard(request):
    """
    Returns dashboard statistics.
    Supports two filter types:
      - "until_date": expects filter_value in YYYY-MM-DD format (daily filter)
      - "month": expects filter_value in YYYY-MM format (full month statistics)
    """
    filter_type = request.GET.get('filter_type')
    filter_value = request.GET.get('filter_value')
    print(f"Filter Type: {filter_type}, Filter Value: {filter_value}")

    if not filter_type or not filter_value:
        return JsonResponse({'error': 'Missing filter_type or filter_value.'}, status=400)

    if filter_type == 'until_date':
        try:
            selected_date = datetime.strptime(filter_value, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid filter_value format. Must be YYYY-MM-DD.'}, status=400)

        daily_delays = DelayData.objects.filter(date=selected_date).count()
        daily_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__date=selected_date).count()

        monthly_delays = DelayData.objects.filter(date__year=selected_date.year,
                                                   date__month=selected_date.month).count()
        monthly_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__year=selected_date.year,
                                                             breakdown_datetime__month=selected_date.month).count()

        yearly_delays = DelayData.objects.filter(date__year=selected_date.year).count()
        yearly_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__year=selected_date.year).count()

    elif filter_type == 'month':
        # Expecting filter_value in "YYYY-MM" format.
        try:
            year_str, month_str = filter_value.split('-')
            selected_year = int(year_str)
            selected_month = int(month_str)
            selected_date = date(selected_year, selected_month, 1)
        except Exception:
            return JsonResponse({'error': 'Invalid filter_value format. Must be YYYY-MM.'}, status=400)

        # For a full month, count all records within that month.
        daily_delays = DelayData.objects.filter(date=selected_date).count()  # (if needed)
        daily_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__date=selected_date).count()

        monthly_delays = DelayData.objects.filter(date__year=selected_year,
                                                   date__month=selected_month).count()
        monthly_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__year=selected_year,
                                                             breakdown_datetime__month=selected_month).count()

        yearly_delays = DelayData.objects.filter(date__year=selected_year).count()
        yearly_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__year=selected_year).count()
    else:
        return JsonResponse({'error': 'Invalid filter type. Expected "until_date" or "month".'}, status=400)

    return JsonResponse({
        'daily_delays': daily_delays,
        'daily_breakdowns': daily_breakdowns,
        'monthly_delays': monthly_delays,
        'monthly_breakdowns': monthly_breakdowns,
        'yearly_delays': yearly_delays,
        'yearly_breakdowns': yearly_breakdowns,
        'chart_data': generate_chart_data(  # Assumes you have this helper function defined.
            daily_delays, daily_breakdowns, monthly_delays, monthly_breakdowns, yearly_delays, yearly_breakdowns
        )
    })



def generate_chart_data(daily_delays, daily_breakdowns, monthly_delays, monthly_breakdowns, yearly_delays, yearly_breakdowns):
    """Generate chart data for the response."""
    return {
        'labels': ['Daily', 'Monthly', 'Yearly'],
        'datasets': [
            {
                'label': 'Delays',
                'data': [daily_delays, monthly_delays, yearly_delays],
                'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1
            },
            {
                'label': 'Breakdowns',
                'data': [daily_breakdowns, monthly_breakdowns, yearly_breakdowns],
                'backgroundColor': 'rgba(255, 99, 132, 0.6)',
                'borderColor': 'rgba(255, 99, 132, 1)',
                'borderWidth': 1
            }
        ]
    }

# View function that skips authentication:
from django.shortcuts import render
from .models import DelayData, BreakdownReport
from django.db.models import Count, ExpressionWrapper, DurationField, F
from datetime import timedelta

def public_stm_dashboard(request):
    logger.info("Accessing public STM dashboard.")
    start_of_month = now().replace(day=1).date()
    today = now().date()
    
    try:
        delayed_trips = (
            DelayData.objects.annotate(
                delay_duration=ExpressionWrapper(F('ata') - F('sta'), output_field=DurationField())
            )
            .filter(date__gte=start_of_month, date__lte=today, delay_duration__gt=timedelta(minutes=30))
            .annotate(delay_count=Count('id'))
            .values('route', 'sta', 'delay_count')
            .order_by('-delay_count')
        )
        logger.info(f"Delayed trips fetched: {len(delayed_trips)}")

    except Exception as e:
        logger.error(f"Error fetching delayed trips: {e}")
        delayed_trips = []

    for trip in delayed_trips:
        trip['sta'] = str(trip['sta'])

    return render(request, 'duty/STM_dashboard.html', {'delayed_trips': delayed_trips})




from django.shortcuts import render
from .forms import BusKmTrackingForm

def submit_bus_km(request):
    success = False  # Flag to indicate a successful submission

    if request.method == "POST":
        form = BusKmTrackingForm(request.POST)
        if form.is_valid():
            form.save()
            success = True  # Set flag on successful save
            form = BusKmTrackingForm()  # Reset form after saving
    else:
        form = BusKmTrackingForm()
    
    context = {
        'form': form,
        'success': success,
    }
    return render(request, 'duty/submit_bus_km.html', context)


from django.shortcuts import render, redirect
from .forms import BusKmTrackingForm
# (Assume you have a DriverTripForm or formset for driver trip details.)
# from .forms import DriverTripForm  # Uncomment and use if needed

def submit_driver_trip(request):
    """
    Step 1: Process driver trip (head count) details.
    After processing, redirect to the bus & km details page.
    """
    if request.method == "POST":
        # --- Process and save the driver trip details here ---
        # For example, if using a form or formset:
        #
        # form = DriverTripForm(request.POST)
        # if form.is_valid():
        #     form.save()
        #
        # Alternatively, process a formset.
        #
        # (For this example, we assume the data is processed.)
        
        # After processing head count details, redirect:
        return redirect('submit_bus_km')
    
    # Render the head count page.
    # (This template is provided below.)
    context = {
        # Pass any context variables (e.g., error_message, success_message) if needed.
    }
    return render(request, 'duty/enter_head_count.html', context)


def submit_bus_km(request):
    """
    Step 2: Render and process the Bus & Km details form.
    After successful submission, show a success message on the same page.
    """
    success = False  # Flag to indicate successful save
    if request.method == "POST":
        form = BusKmTrackingForm(request.POST)
        if form.is_valid():
            form.save()
            success = True
            # Optionally, reset the form after saving
            form = BusKmTrackingForm()
    else:
        form = BusKmTrackingForm()
    
    context = {
        'form': form,
        'success': success,
    }
    return render(request, 'duty/submit_bus_km.html', context)
