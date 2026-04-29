import calendar
import logging
from datetime import date, datetime, timedelta

from openpyxl import Workbook

from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.timezone import localdate, now

from ..models import BreakdownReport, DelayData, StmPickupPoint, StmRoute, StmShiftTime

logger = logging.getLogger(__name__)


def stm_dashboard(request):
    start_of_month = now().replace(day=1).date()
    today = now().date()

    delayed_trips = list(
        DelayData.objects.annotate(
            delay_duration=ExpressionWrapper(F('ata') - F('sta'), output_field=DurationField())
        )
        .filter(date__gte=start_of_month, date__lte=today, delay_duration__gt=timedelta(minutes=30))
        .annotate(delay_count=Count('id'))
        .values('route', 'sta', 'delay_count')
        .order_by('-delay_count')
    )
    for trip in delayed_trips:
        trip['sta'] = str(trip['sta'])

    return render(request, 'duty/STM_dashboard.html', {'delayed_trips': delayed_trips})


def fleet_counts_api(request):
    today = localdate()
    month_start = today.replace(day=1)
    return JsonResponse({
        'daily_delay_count': DelayData.objects.filter(date=today).count(),
        'monthly_delay_count': DelayData.objects.filter(date__gte=month_start).count(),
        'daily_breakdown_count': BreakdownReport.objects.filter(breakdown_datetime__date=today).count(),
        'monthly_breakdown_count': BreakdownReport.objects.filter(breakdown_datetime__date__gte=month_start).count(),
        'total_delay_count': DelayData.objects.count(),
        'total_breakdown_count': BreakdownReport.objects.count(),
    })


def download_fleet_report(request):
    report_type = request.GET.get('report_type')
    report_category = request.GET.get('report_category')

    if not report_type or not report_category:
        return JsonResponse({'status': 'error', 'message': 'Invalid report type or category.'})

    today = now().date()
    month_start = today.replace(day=1)
    queryset = None

    if report_type == 'daily':
        queryset = DelayData.objects.filter(date=today) if report_category == 'delay' else BreakdownReport.objects.filter(breakdown_datetime__date=today)
    elif report_type == 'monthly':
        queryset = DelayData.objects.filter(date__gte=month_start) if report_category == 'delay' else BreakdownReport.objects.filter(breakdown_datetime__date__gte=month_start)
    elif report_type == 'total':
        queryset = DelayData.objects.all() if report_category == 'delay' else BreakdownReport.objects.all()

    if queryset is None or not queryset.exists():
        return JsonResponse({'status': 'error', 'message': 'No data available for the selected report.'})

    workbook = Workbook()
    worksheet = workbook.active

    if report_category == 'delay':
        worksheet.append(['Date', 'Route', 'In/Out', 'STD', 'STA', 'ATD', 'ATA', 'Delay', 'Remarks', 'Staff Count'])
        for d in queryset:
            worksheet.append([
                d.date, d.route, d.in_out,
                d.std.strftime('%H:%M') if d.std else None,
                d.sta.strftime('%H:%M') if d.sta else None,
                d.atd.strftime('%H:%M') if d.atd else None,
                d.ata.strftime('%H:%M') if d.ata else None,
                d.delay, d.remarks, d.staff_count,
            ])
    elif report_category == 'breakdown':
        worksheet.append([
            'Report Date', 'Breakdown Date', 'Location', 'Route #', 'Trip Work Order',
            'Passengers Involved', 'EK Staff Numbers', 'Non-EK Passenger Details',
            'Injured Passengers', 'Action Taken for Injured', 'Vehicle Damage',
            'Driver Name', 'Driver ID', 'Driver Shift', 'Breakdown Description',
            'EK Vehicles Involved', 'Vehicle Make and Plate', 'Replacement Vehicle',
            'Reported To', 'Reported Date',
        ])
        for b in queryset:
            worksheet.append([
                b.reported_datetime.strftime('%Y-%m-%d %H:%M'),
                b.breakdown_datetime.strftime('%Y-%m-%d %H:%M'),
                b.location, b.route_number, b.trip_work_order, b.passengers_involved,
                b.ek_staff_numbers, b.non_ek_passenger_details, b.injured_passengers,
                b.action_taken_for_injured, b.vehicle_damage, b.driver_name, b.driver_id,
                b.driver_shift, b.breakdown_description, b.ek_vehicles_involved,
                b.vehicle_make_plate, b.replacement_vehicle, b.reported_to_person,
                b.reported_datetime.strftime('%Y-%m-%d %H:%M'),
            ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{report_category}_{report_type}_report.xlsx"'
    workbook.save(response)
    return response


def ajax_search_route(request):
    if request.method != 'GET':
        return render(request, 'duty/error_page.html', {'error': 'Invalid request'})

    route_code = request.GET.get('route', '').strip()
    route_name = request.GET.get('route_name', '').strip()
    route_type = request.GET.get('type', '').strip()
    work_hub = request.GET.get('work_hub', '').strip()
    pick_up_point = request.GET.get('pick_up_point', '').strip()
    stop_id = request.GET.get('stop_id', '').strip()
    shift_time = request.GET.get('shift_time', '').strip()
    connection_from = request.GET.get('connection_from', '').strip()
    connection_to = request.GET.get('connection_to', '').strip()

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

    routes = StmRoute.objects.filter(query).distinct()
    route_data = []
    seen_entries = set()

    for route in routes:
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

        if pickup_points.exists() or not pick_up_point:
            for shift in shift_times:
                key = (route.route, route.route_type, shift.shift_time, route.work_hub)
                if key not in seen_entries:
                    seen_entries.add(key)
                    route_data.append({
                        'route_code': route.route,
                        'route_name': route.route,
                        'route_type': route.route_type,
                        'work_hub': route.work_hub,
                        'connection_from': route.connection_from,
                        'connection_to': route.connection_to,
                        'shift_time': shift.shift_time.strftime('%H:%M') if shift.shift_time else '-',
                        'link': (
                            f"/route-details/?route={route.route}"
                            f"&shift_time={shift.shift_time.strftime('%H:%M') if shift.shift_time else ''}"
                            f"&type={route.route_type}"
                        ),
                    })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'routes': route_data})
    return render(request, 'duty/search_form_with_results.html', {'routes': route_data})


def route_details(request):
    route_name = request.GET.get('route')
    route_type = request.GET.get('type')
    shift_time = request.GET.get('shift_time')

    if not route_name:
        return render(request, 'duty/error_page.html', {'error': 'Route is missing.'})
    if not shift_time:
        return render(request, 'duty/error_page.html', {'error': 'Shift time is missing.'})

    if not route_type:
        qs = StmRoute.objects.filter(route__iexact=route_name).distinct()
        if qs.count() == 1:
            route_type = qs.first().route_type
        else:
            return render(request, 'duty/error_page.html', {'error': 'Route type is missing and cannot be inferred.'})

    route_qs = StmRoute.objects.filter(route__iexact=route_name, route_type__iexact=route_type)
    if not route_qs.exists():
        return render(request, 'duty/error_page.html', {'error': 'No matching route found.'})

    route_data_list = []
    for route in route_qs:
        shift_times = StmShiftTime.objects.filter(route=route, shift_time=shift_time).order_by('stop_order')
        if not shift_times.exists():
            continue

        stop_order_to_times = {
            s.stop_order: {
                'time': s.time if isinstance(s.time, str) else (s.time.strftime('%H:%M') if s.time else '-'),
                'special_time': s.special_time if isinstance(s.special_time, str) else (s.special_time.strftime('%H:%M') if s.special_time else '-'),
            }
            for s in shift_times
        }
        pickup_points = StmPickupPoint.objects.filter(route=route).order_by('pick_up_point_order_id')
        route_data_list.append({
            'route_name': route.route,
            'route_type': route.route_type,
            'operating_days_1': route.operating_days_1,
            'operating_days_2': route.operating_days_2,
            'work_hub': route.work_hub,
            'shift_time': shift_time,
            'pickup_points': [
                {
                    'stop_id': p.stop_id,
                    'pick_up_point': p.pick_up_point,
                    'time': stop_order_to_times.get(p.pick_up_point_order_id, {}).get('time', '-'),
                    'special_time': stop_order_to_times.get(p.pick_up_point_order_id, {}).get('special_time', '-'),
                }
                for p in pickup_points
            ],
        })

    return render(request, 'duty/stm_timetable.html', {'route_data_list': route_data_list})


def stm_timetables(request):
    route_name = request.GET.get('route')
    shift_time = request.GET.get('shift_time')

    if not route_name or not shift_time:
        return render(request, 'duty/stm_timetable.html', {'error': 'Invalid route or shift time provided'})

    routes = StmRoute.objects.filter(route__iexact=route_name)
    if not routes.exists():
        return render(request, 'duty/stm_timetable.html', {'error': 'No matching route found.'})

    route_data_list = []
    for route in routes:
        shift = StmShiftTime.objects.filter(route=route, shift_time=shift_time).first()
        if not shift:
            continue

        pickup_points = StmPickupPoint.objects.filter(route=route).order_by('pick_up_point_order_id')
        stop_order_to_time = {
            s.stop_order: s.time if isinstance(s.time, str) else (s.time.strftime('%H:%M') if s.time else '-')
            for s in StmShiftTime.objects.filter(route=route).order_by('stop_order')
        }
        route_data_list.append({
            'route_name': route.route,
            'route_type': route.route_type,
            'operating_days_1': route.operating_days_1,
            'operating_days_2': route.operating_days_2,
            'work_hub': route.work_hub,
            'shift_time': shift.shift_time if isinstance(shift.shift_time, str) else (shift.shift_time.strftime('%H:%M') if shift.shift_time else 'N/A'),
            'pickup_points': [
                {
                    'stop_id': p.stop_id,
                    'pick_up_point': p.pick_up_point,
                    'time': stop_order_to_time.get(p.pick_up_point_order_id, '-'),
                    'special_time': shift.special_time if isinstance(shift.special_time, str) else (shift.special_time.strftime('%H:%M') if shift.special_time else '-'),
                }
                for p in pickup_points
            ],
        })

    if route_data_list:
        return render(request, 'duty/stm_timetable.html', {'route_data_list': route_data_list})
    return render(request, 'duty/stm_timetable.html', {'error': 'No matching shift time found for the selected route.'})


def get_most_delayed_trips_api(request):
    selected_month_str = request.GET.get('selected_month')
    if selected_month_str:
        try:
            year, month = selected_month_str.split('-')
            year, month = int(year), int(month)
            last_day = calendar.monthrange(year, month)[1]
            month_start = date(year, month, 1)
            month_end = date(year, month, last_day)
        except Exception:
            today = now().date()
            month_start = today.replace(day=1)
            month_end = today
    else:
        selected_date_str = request.GET.get('selected_date')
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date() if selected_date_str else now().date()
        except ValueError:
            selected_date = now().date()
        month_start = selected_date.replace(day=1)
        month_end = selected_date

    delayed_trips = list(
        DelayData.objects.filter(date__gte=month_start, date__lte=month_end)
        .values('route', 'sta')
        .annotate(delay_count=Count('id'))
        .order_by('-delay_count')[:5]
    )
    for trip in delayed_trips:
        trip['sta'] = str(trip['sta'])
    return JsonResponse(delayed_trips, safe=False)


def get_otp_chart_data(request):
    period = request.GET.get("period", "daily").lower()
    selected_month_str = request.GET.get("selected_month")

    if selected_month_str:
        try:
            year, month = selected_month_str.split('-')
            selected_date = date(int(year), int(month), 1)
        except Exception:
            selected_date = now().date().replace(day=1)
    else:
        selected_date_str = request.GET.get("selected_date")
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date() if selected_date_str else (
                now().date().replace(day=1) if period == "monthly" else now().date()
            )
        except ValueError:
            selected_date = now().date()

    qs = DelayData.objects.all()
    if period == "daily":
        qs = qs.filter(date=selected_date)
    elif period == "monthly":
        selected_date = selected_date.replace(day=1)
        last_day = calendar.monthrange(selected_date.year, selected_date.month)[1]
        qs = qs.filter(date__gte=selected_date, date__lte=selected_date.replace(day=last_day))
    elif period == "yearly":
        qs = qs.filter(date__gte=selected_date.replace(month=1, day=1), date__lte=selected_date)
    else:
        qs = qs.filter(date=selected_date)

    qs = qs.annotate(delay_duration=ExpressionWrapper(F("atd") - F("std"), output_field=DurationField()))
    total_count = qs.count()
    failure_count = qs.filter(delay_duration__gt=timedelta(minutes=10)).count()
    return JsonResponse({"labels": ["On Time", "Not On Time"], "data": [total_count - failure_count, failure_count]})


def filter_dashboard(request):
    filter_type = request.GET.get('filter_type')
    filter_value = request.GET.get('filter_value')

    if not filter_type or not filter_value:
        return JsonResponse({'error': 'Missing filter_type or filter_value.'}, status=400)

    if filter_type == 'until_date':
        try:
            selected_date = datetime.strptime(filter_value, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid filter_value format. Must be YYYY-MM-DD.'}, status=400)
        year, month = selected_date.year, selected_date.month

    elif filter_type == 'month':
        try:
            year, month = map(int, filter_value.split('-'))
            selected_date = date(year, month, 1)
        except Exception:
            return JsonResponse({'error': 'Invalid filter_value format. Must be YYYY-MM.'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid filter type.'}, status=400)

    daily_delays = DelayData.objects.filter(date=selected_date).count()
    daily_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__date=selected_date).count()
    monthly_delays = DelayData.objects.filter(date__year=year, date__month=month).count()
    monthly_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__year=year, breakdown_datetime__month=month).count()
    yearly_delays = DelayData.objects.filter(date__year=year).count()
    yearly_breakdowns = BreakdownReport.objects.filter(breakdown_datetime__year=year).count()

    return JsonResponse({
        'daily_delays': daily_delays,
        'daily_breakdowns': daily_breakdowns,
        'monthly_delays': monthly_delays,
        'monthly_breakdowns': monthly_breakdowns,
        'yearly_delays': yearly_delays,
        'yearly_breakdowns': yearly_breakdowns,
        'chart_data': {
            'labels': ['Daily', 'Monthly', 'Yearly'],
            'datasets': [
                {'label': 'Delays', 'data': [daily_delays, monthly_delays, yearly_delays], 'backgroundColor': 'rgba(75, 192, 192, 0.6)', 'borderColor': 'rgba(75, 192, 192, 1)', 'borderWidth': 1},
                {'label': 'Breakdowns', 'data': [daily_breakdowns, monthly_breakdowns, yearly_breakdowns], 'backgroundColor': 'rgba(255, 99, 132, 0.6)', 'borderColor': 'rgba(255, 99, 132, 1)', 'borderWidth': 1},
            ],
        },
    })


def public_stm_dashboard(request):
    date_str = request.GET.get('date')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
    except ValueError:
        selected_date = datetime.now().date()

    start_of_month = selected_date.replace(day=1)
    try:
        delayed_trips = list(
            DelayData.objects.annotate(
                delay_duration=ExpressionWrapper(F('ata') - F('sta'), output_field=DurationField())
            )
            .filter(date__gte=start_of_month, date__lte=selected_date, delay_duration__gt=timedelta(minutes=30))
            .annotate(delay_count=Count('id'))
            .values('route', 'sta', 'delay_count')
            .order_by('-delay_count')
        )
        for trip in delayed_trips:
            trip['sta'] = str(trip['sta'])
    except Exception as e:
        logger.error(f"Error fetching delayed trips: {e}")
        delayed_trips = []

    return render(request, 'duty/STM_dashboard.html', {
        'delayed_trips': delayed_trips,
        'selected_date': selected_date,
    })


def get_top_delayed_load_trips_api(request):
    selected_date_str = request.GET.get('selected_date')
    selected_month_str = request.GET.get('selected_month')

    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        month_start, month_end = selected_date.replace(day=1), selected_date
    elif selected_month_str:
        year, month = map(int, selected_month_str.split('-'))
        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])
    else:
        month_start = datetime.now().date().replace(day=1)
        month_end = datetime.now().date()

    delayed_trips = (
        DelayData.objects.filter(date__gte=month_start, date__lte=month_end)
        .annotate(delay_duration=F('ata') - F('sta'))
        .filter(delay_duration__gt=timedelta(minutes=0))
        .values('route', 'sta')
        .annotate(staff_count=Sum('staff_count'), delay_count=Count('id'))
        .order_by('-staff_count')[:5]
    )
    return JsonResponse(
        [{'route': t['route'], 'sta': str(t['sta']), 'staff_count': t['staff_count'], 'delay_count': t['delay_count']} for t in delayed_trips],
        safe=False,
    )


def get_daily_delay_details(request):
    date_str = request.GET.get('date', now().date().isoformat())
    delays = DelayData.objects.filter(date=date_str)
    return JsonResponse([
        {
            'date': d.date.strftime('%Y-%m-%d'),
            'route': d.route,
            'in_out': d.in_out,
            'sta': str(d.sta) if d.sta else None,
            'ata': str(d.ata) if d.ata else None,
            'std': str(d.std) if d.std else None,
            'atd': str(d.atd) if d.atd else None,
            'staff_count': d.staff_count,
            'remarks': d.remarks,
        }
        for d in delays
    ], safe=False)


def get_otp_details(request):
    period = request.GET.get("period", "daily").lower()
    status = request.GET.get("status", "").upper()
    selected_month_str = request.GET.get("selected_month")
    exclude_early = request.GET.get("exclude_early", "false").lower() == "true"

    if selected_month_str:
        try:
            year, month = selected_month_str.split('-')
            selected_date = date(int(year), int(month), 1)
        except Exception:
            selected_date = now().date().replace(day=1)
    else:
        selected_date_str = request.GET.get("selected_date")
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date() if selected_date_str else (
                now().date().replace(day=1) if period == "monthly" else now().date()
            )
        except ValueError:
            selected_date = now().date()

    qs = DelayData.objects.all()
    if period == "daily":
        qs = qs.filter(date=selected_date)
        period_label = "daily"
    elif period == "monthly":
        selected_date = selected_date.replace(day=1)
        last_day = calendar.monthrange(selected_date.year, selected_date.month)[1]
        qs = qs.filter(date__gte=selected_date, date__lte=selected_date.replace(day=last_day))
        period_label = "monthly"
    elif period == "yearly":
        qs = qs.filter(date__gte=selected_date.replace(month=1, day=1), date__lte=selected_date)
        period_label = "yearly"
    else:
        return JsonResponse({'error': 'Invalid period. Use "daily", "monthly", or "yearly".'}, status=400)

    qs = qs.filter(std__isnull=False, atd__isnull=False).annotate(
        delay_duration=ExpressionWrapper(F("atd") - F("std"), output_field=DurationField())
    )
    if status == "OT":
        qs = qs.filter(delay_duration__gte=timedelta(minutes=0), delay_duration__lte=timedelta(minutes=10)) if exclude_early else qs.filter(delay_duration__lte=timedelta(minutes=10))
    elif status == "NST":
        qs = qs.filter(delay_duration__gt=timedelta(minutes=10))
    else:
        return JsonResponse({'error': 'Invalid status. Use "OT" or "NST".'}, status=400)

    delay_details = [
        {
            'date': d.date.strftime('%Y-%m-%d'),
            'route': d.route,
            'in_out': d.in_out,
            'std': str(d.std) if d.std else None,
            'atd': str(d.atd) if d.atd else None,
            'sta': str(d.sta) if d.sta else None,
            'ata': str(d.ata) if d.ata else None,
            'staff_count': d.staff_count,
            'remarks': d.remarks,
        }
        for d in qs
    ]

    if not delay_details:
        return JsonResponse({'message': f'No {status} details available for the selected {period_label} period.'}, safe=False)
    return JsonResponse(delay_details, safe=False)
