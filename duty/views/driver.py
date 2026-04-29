import logging
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect

from ..forms import DriverTripFormSet
from ..models import BusKmTracking, DriverImportLog, DriverTrip, DutyCardTrip

logger = logging.getLogger(__name__)


@login_required
def home(request):
    staff_id = request.user.username
    staff_name = (
        DriverImportLog.objects.filter(staff_id=staff_id)
        .values_list('driver_name', flat=True)
        .first() or staff_id
    )
    driver_trips = DriverTrip.objects.filter(driver__staff_id=staff_id)
    driver_trip_data = [
        {
            'route_name': trip.route_name,
            'pick_up_time': trip.pick_up_time.strftime('%H:%M:%S'),
            'drop_off_time': trip.drop_off_time.strftime('%H:%M:%S'),
            'shift_time': trip.shift_time.strftime('%H:%M:%S'),
            'head_count': trip.head_count,
            'trip_type': trip.trip_type,
            'date': trip.date.strftime('%Y-%m-%d'),
        }
        for trip in driver_trips
    ]
    return render(request, 'duty/home.html', {
        'staff_name': staff_name,
        'driver_trips': driver_trip_data,
    })


@login_required
def submission_history(request):
    staff_id = request.user.username
    driver = DriverImportLog.objects.filter(staff_id=staff_id).first()

    if not driver:
        return render(request, 'duty/user_submission_history.html', {
            'error_message': "No submission history found for this user."
        })

    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year, month = today.year, today.month

    head_count_entries = DriverTrip.objects.filter(
        driver=driver, date__year=year, date__month=month
    ).order_by('-date')

    bus_km_entries = BusKmTracking.objects.filter(
        driver=driver, submission_date__year=year, submission_date__month=month
    ).order_by('-submission_date')

    return render(request, 'duty/user_submission_history.html', {
        'staff_name': driver.driver_name,
        'head_count_entries': head_count_entries,
        'bus_km_entries': bus_km_entries,
        'filter_year': year,
        'filter_month': month,
        'months': range(1, 13),
        'years': range(2020, today.year + 1),
    })


@login_required
def enter_head_count(request):
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

        if not duty_card_no:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Please fill in the Duty Card No.",
            })

        duty_card = DutyCardTrip.objects.filter(duty_card_no=duty_card_no).first()
        if not duty_card:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Invalid Duty Card No. Please check and try again.",
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
                'error_message': "Invalid date format. Please use YYYY-MM-DD.",
            })

        if DriverTrip.objects.filter(driver=driver, date=desired_date).exists():
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': f"Duty card already submitted for {desired_date}. Cannot submit twice for the same date.",
            })

        if trip_formset.is_valid():
            for form in trip_formset:
                trip = form.save(commit=False)
                trip.driver = driver
                trip.duty_card = duty_card
                trip.save()
            return redirect('submit_bus_km')
        else:
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'staff_name': staff_name,
                'error_message': "Please correct the errors below.",
            })

    trip_formset = DriverTripFormSet(prefix='drivertrip_set')
    return render(request, 'duty/enter_head_count.html', {
        'trip_formset': trip_formset,
        'staff_name': staff_name,
    })


@login_required
def success(request):
    return render(request, 'duty/success.html')


def staff_id_autocomplete(request):
    if 'term' in request.GET:
        qs = DriverImportLog.objects.filter(staff_id__icontains=request.GET['term'])
        return JsonResponse(list(qs.values_list('staff_id', flat=True)), safe=False)
    return JsonResponse([], safe=False)


def get_driver_name(request):
    staff_id = request.GET.get('staff_id')
    if staff_id:
        driver_log = DriverImportLog.objects.filter(staff_id=staff_id).first()
        if driver_log:
            return JsonResponse({'driver_name': driver_log.driver_name})
    return JsonResponse({'driver_name': ''})


def duty_card_no_autocomplete(request):
    if 'term' in request.GET:
        qs = (
            DutyCardTrip.objects.filter(duty_card_no__icontains=request.GET['term'])
            .values_list('duty_card_no', flat=True)
            .distinct()
        )
        return JsonResponse(list(qs), safe=False)
    return JsonResponse([], safe=False)


@login_required
def get_duty_card_details(request):
    if 'duty_card_no' not in request.GET:
        return JsonResponse({'error': 'Duty card number not provided'}, status=400)

    duty_card_no = request.GET['duty_card_no']
    trips = DutyCardTrip.objects.filter(duty_card_no=duty_card_no).order_by('pick_up_time')

    if not trips.exists():
        return JsonResponse({'error': 'No trips found for the provided duty card number.'}, status=404)

    trip_details = []
    for trip in trips:
        normalized_type = 'inbound' if trip.trip_type and trip.trip_type.lower() in ['in', 'inbound'] else 'outbound'
        trip_details.append({
            'route_name': trip.route_name,
            'pick_up_time': trip.pick_up_time.strftime("%H:%M") if trip.pick_up_time else '',
            'drop_off_time': trip.drop_off_time.strftime("%H:%M") if trip.drop_off_time else '',
            'shift_time': trip.shift_time.strftime("%H:%M") if trip.shift_time else '',
            'trip_type': normalized_type,
            'date': datetime.today().strftime("%Y-%m-%d"),
            'head_count': 0,
            'details_link': (
                f"/route-details/?route={trip.route_name}"
                f"&shift_time={trip.shift_time.strftime('%H:%M') if trip.shift_time else ''}"
                f"&type={normalized_type}"
            ),
        })
    return JsonResponse({'trips': trip_details}, safe=False)


@login_required
def route_autocomplete(request):
    if 'term' in request.GET:
        qs = DriverTrip.objects.filter(route_name__istartswith=request.GET['term'])
        return JsonResponse(list(qs.values_list('route_name', flat=True).distinct()), safe=False)
    return JsonResponse([], safe=False)


@login_required
def shift_time_autocomplete(request):
    if 'term' in request.GET:
        try:
            parsed_time = datetime.strptime(request.GET['term'], "%H:%M").time()
            qs = DriverTrip.objects.filter(shift_time__startswith=parsed_time)
            shift_times = [t.strftime("%H:%M") for t in qs.values_list('shift_time', flat=True).distinct()]
        except ValueError:
            shift_times = []
        return JsonResponse(shift_times, safe=False)
    return JsonResponse([], safe=False)
