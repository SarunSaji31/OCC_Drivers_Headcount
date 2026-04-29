import logging
from datetime import date, datetime

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.forms import formset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from ..decorators import admin_required
from ..forms import BreakdownReportForm, DelayDataForm, DriverTripFormSet
from ..models import BusKmTracking, BreakdownReport, DelayData, DriverImportLog, DriverTrip, DutyCardTrip

logger = logging.getLogger(__name__)


@login_required
@admin_required
def report_view(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')

        route_filter = request.GET.get('routeFilter')
        trip_type_filter = request.GET.get('tripTypeFilter')
        shift_time_filter = request.GET.get('shiftTimeFilter')
        date_range = request.GET.get('dateRange')

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
                driver_trips = driver_trips.filter(shift_time=datetime.strptime(shift_time_filter, '%H:%M').time())
            except ValueError:
                pass

        if date_range:
            try:
                start_str, end_str = date_range.split(' - ')
                driver_trips = driver_trips.filter(date__range=(
                    datetime.strptime(start_str, '%Y-%m-%d').date(),
                    datetime.strptime(end_str, '%Y-%m-%d').date(),
                ))
            except ValueError:
                return HttpResponse("Invalid date range format", status=400)

        order_column_index = int(request.GET.get('order[0][column]', 8))
        order_direction = request.GET.get('order[0][dir]', 'asc')
        orderable_fields = [
            'driver__staff_id', 'driver__driver_name', 'duty_card__duty_card_no',
            'route_name', 'pick_up_time', 'drop_off_time', 'shift_time',
            'trip_type', 'date', 'head_count',
        ]
        order_col = orderable_fields[order_column_index]
        if order_direction == 'desc':
            order_col = f'-{order_col}'
        driver_trips = driver_trips.order_by(order_col)

        paginator = Paginator(driver_trips, length)
        page_obj = paginator.get_page((start // length) + 1)

        data = [
            {
                'staff_id': trip.driver.staff_id,
                'driver_name': trip.driver.driver_name,
                'duty_card_no': trip.duty_card.duty_card_no,
                'route_name': trip.route_name,
                'pick_up_time': trip.pick_up_time.strftime('%H:%M') if trip.pick_up_time else '',
                'drop_off_time': trip.drop_off_time.strftime('%H:%M') if trip.drop_off_time else '',
                'shift_time': trip.shift_time.strftime('%H:%M') if trip.shift_time else '',
                'trip_type': trip.trip_type,
                'date': trip.date.strftime('%Y-%m-%d'),
                'head_count': trip.head_count,
            }
            for trip in page_obj
        ]
        return JsonResponse({
            'draw': draw,
            'recordsTotal': driver_trips.count(),
            'recordsFiltered': driver_trips.count(),
            'data': data,
        })

    return render(request, 'duty/report_data.html', {'title': 'Driver Trip Report'})


@login_required
def download_report(request):
    date_range = request.GET.get('daterange')
    route_filter = request.GET.get('route')
    shift_time_filter = request.GET.get('shift_time')
    trip_type_filter = request.GET.get('trip_type')

    driver_trips = DriverTrip.objects.all()

    if date_range:
        try:
            start_str, end_str = date_range.split(' - ')
            driver_trips = driver_trips.filter(date__range=(
                datetime.strptime(start_str, '%Y-%m-%d').date(),
                datetime.strptime(end_str, '%Y-%m-%d').date(),
            ))
        except ValueError:
            return HttpResponse("Invalid date range format", status=400)

    if route_filter:
        driver_trips = driver_trips.filter(route_name=route_filter)
    if shift_time_filter:
        driver_trips = driver_trips.filter(shift_time=shift_time_filter)
    if trip_type_filter:
        driver_trips = driver_trips.filter(trip_type=trip_type_filter)

    data = [
        {
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
        }
        for trip in driver_trips
    ]
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=driver_trip_report_{date_range}.xlsx'
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Driver Trips', index=False)
    return response


@login_required
@admin_required
def admin_dashboard(request):
    return render(request, 'duty/admin_dashboard.html')


@login_required
@admin_required
def dashboard_data(request):
    date_filter = request.GET.get('date') or date.today()
    shift_filter = request.GET.get('shift')
    type_filter = request.GET.get('type')

    trips = DriverTrip.objects.filter(date=date_filter)
    if shift_filter:
        trips = trips.filter(shift_time=shift_filter)
    if type_filter:
        trips = trips.filter(trip_type=type_filter)

    return JsonResponse({
        'total_staff': trips.aggregate(total=Sum('head_count'))['total'] or 0,
        'gd_staff': trips.filter(route_name__startswith='GD').aggregate(s=Sum('head_count'))['s'] or 0,
        'gk_staff': trips.filter(route_name__startswith='GK').aggregate(s=Sum('head_count'))['s'] or 0,
        'ge_staff': trips.filter(route_name__startswith='GE').aggregate(s=Sum('head_count'))['s'] or 0,
        'dwc_staff': trips.filter(route_name__startswith='DWC').aggregate(s=Sum('head_count'))['s'] or 0,
        'cc_staff': trips.filter(route_name__startswith='CC').aggregate(s=Sum('head_count'))['s'] or 0,
    })


def duty_card_submission_data(request):
    date_filter = request.GET.get('date', datetime.today().strftime('%Y-%m-%d'))

    if request.GET.get('download') == 'xlsx':
        return _download_duty_card_data_as_excel(date_filter)

    parsed = datetime.strptime(date_filter, '%Y-%m-%d')
    date_start = timezone.make_aware(datetime.combine(parsed, datetime.min.time()))
    date_end = timezone.make_aware(datetime.combine(parsed, datetime.max.time()))

    total_duty_cards = DutyCardTrip.objects.values('duty_card_no').distinct().count()
    submitted_cards = (
        DriverTrip.objects.filter(date__range=(date_start, date_end))
        .values('duty_card').distinct().count()
    )

    return JsonResponse({
        'total_duty_cards': total_duty_cards,
        'submitted_cards': submitted_cards,
        'pending_cards': max(total_duty_cards - submitted_cards, 0),
        'bus_km_submissions': BusKmTracking.objects.count(),
    })


def _download_duty_card_data_as_excel(date_filter):
    parsed = datetime.strptime(date_filter, '%Y-%m-%d')
    date_start = timezone.make_aware(datetime.combine(parsed, datetime.min.time()))
    date_end = timezone.make_aware(datetime.combine(parsed, datetime.max.time()))

    submitted_nos = set(
        DriverTrip.objects.filter(date__range=(date_start, date_end))
        .values_list('duty_card__duty_card_no', flat=True)
        .distinct()
    )
    data = [
        {
            'Duty Card No': dc['duty_card_no'],
            'Submission Status': 'Submitted' if dc['duty_card_no'] in submitted_nos else 'Pending',
            'Date': date_filter,
        }
        for dc in DutyCardTrip.objects.values('duty_card_no').distinct()
    ]
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=duty_card_details_{date_filter}.xlsx'
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Duty Cards', index=False)
    return response


@login_required
def add_reports(request):
    DelayDataFormSet = formset_factory(DelayDataForm, extra=1)
    if request.method == 'POST':
        formset = DelayDataFormSet(request.POST)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    for form in formset:
                        if form.cleaned_data:
                            form.save()
                return JsonResponse({'status': 'success', 'message': 'Forms saved successfully!'})
            except Exception as e:
                logger.error(f"Error saving forms: {e}")
                return JsonResponse({'status': 'error', 'message': 'An error occurred while saving the forms.'})
        logger.error(f"Formset validation failed: {formset.errors}")
        return JsonResponse({'status': 'error', 'message': 'Invalid form data.', 'errors': formset.errors})

    formset = DelayDataFormSet()
    return render(request, 'duty/Ekg_report.html', {'formset': formset})


@login_required
def add_delay_report(request):
    DelayDataFormSet = formset_factory(DelayDataForm, extra=1)
    if request.method == 'POST':
        formset = DelayDataFormSet(request.POST)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    total_valid = 0
                    for i, form in enumerate(formset):
                        try:
                            instance = form.save(commit=False)
                            d = form.cleaned_data.get('date')
                            sta = form.cleaned_data.get('sta')
                            ata = form.cleaned_data.get('ata')
                            if d and sta and ata:
                                delta = datetime.combine(d, ata) - datetime.combine(d, sta)
                                instance.delay = (datetime.min + delta).time() if delta.total_seconds() >= 0 else None
                            instance.save()
                            total_valid += 1
                        except Exception as e:
                            logger.error(f"Form {i + 1} error: {e}")

                if total_valid == 0:
                    return JsonResponse({'status': 'error', 'message': 'No valid forms submitted.'})
                return JsonResponse({'status': 'success', 'message': f'{total_valid} form(s) processed successfully.'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

        return JsonResponse({'status': 'error', 'message': 'Invalid form data.', 'errors': formset.errors})

    formset = DelayDataFormSet()
    return render(request, 'duty/add_delay_report.html', {'formset': formset})


@login_required
@admin_required
def subcategory_selection(request):
    return render(request, 'duty/subcategory_selection.html')


@login_required
def ekg_breakdown(request):
    if request.method == 'POST':
        form = BreakdownReportForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info("Breakdown Report submitted successfully.")
            return JsonResponse({'status': 'success', 'message': 'Breakdown Report submitted successfully.'})
        logger.error(f"Form validation failed: {form.errors}")
        return JsonResponse({'status': 'error', 'message': 'Invalid form data.', 'errors': form.errors.as_json()})
    form = BreakdownReportForm()
    return render(request, 'duty/ekg_breakdown.html', {'form': form})
