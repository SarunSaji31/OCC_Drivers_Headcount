import logging
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, IntegerField, Q, Sum
from django.db.models.functions import Cast
from django.http import JsonResponse
from django.shortcuts import render, redirect

from ..forms import BusKmTrackingForm
from ..models import (
    BusMasterList, DriverImportLog, DutyCardTrip,
    EKSTMDailyTrips, EKSTMMileage, EKSTMSalik, Unit,
)

logger = logging.getLogger(__name__)


@login_required
def submit_bus_km(request):
    driver = DriverImportLog.objects.get(staff_id=request.user.username)
    today_date = date.today()

    if request.method == "POST":
        form = BusKmTrackingForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.driver = driver
            if not entry.submission_date:
                entry.submission_date = today_date
            entry.save()
            return redirect('home')
    else:
        form = BusKmTrackingForm(initial={'submission_date': today_date})

    return render(request, 'duty/submit_bus_km.html', {'form': form})


def duty_card_suggestions(request):
    term = request.GET.get('term', '')
    suggestions = list(
        DutyCardTrip.objects.filter(duty_card_no__icontains=term)
        .values_list('duty_card_no', flat=True)
        .distinct()
    )
    return JsonResponse(suggestions, safe=False)


def bus_no_suggestions(request):
    term = request.GET.get('term', '')
    suggestions = list(
        BusMasterList.objects.filter(bus_no__icontains=term)
        .values_list('bus_no', flat=True)
        .distinct()
    )
    return JsonResponse(suggestions, safe=False)


def bus_trip_details(request, bus_code):
    date_str = request.GET.get('date')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        selected_date = datetime.today().date()

    trips = EKSTMDailyTrips.objects.filter(
        ride_date=selected_date, unit__code=bus_code
    ).values('route_id', 'route_type', 'shift_in', 'shift_out', 'ride_date')

    trip_list = []
    for trip in trips:
        route_type = trip['route_type'].lower()
        raw_time = trip['shift_in'] if route_type == 'inbound' else trip['shift_out']
        if not raw_time:
            continue
        parsed_time = None
        for fmt in ('%H:%M', '%H:%M:%S'):
            try:
                parsed_time = datetime.strptime(raw_time, fmt).time()
                break
            except ValueError:
                continue
        if parsed_time:
            trip_list.append({
                'route_id': trip['route_id'],
                'route_type': route_type.capitalize(),
                'time': parsed_time.strftime('%H:%M'),
                'date': trip['ride_date'].strftime('%Y-%m-%d'),
            })

    return JsonResponse(sorted(trip_list, key=lambda x: x['time']), safe=False)


def ekstm_47seater_report_dashboard(request):
    date_str = request.GET.get('date')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        selected_date = datetime.today().date()

    previous_date = selected_date - timedelta(days=1)
    current_month_start = selected_date.replace(day=1)
    three_days_ago = selected_date - timedelta(days=3)

    units = Unit.objects.all().order_by('code').annotate(
        count=Count('ekstmdailytrips', filter=Q(ekstmdailytrips__ride_date=selected_date)),
        inbound_count=Count('ekstmdailytrips', filter=Q(ekstmdailytrips__ride_date=selected_date, ekstmdailytrips__route_type__iexact='inbound')),
        outbound_count=Count('ekstmdailytrips', filter=Q(ekstmdailytrips__ride_date=selected_date, ekstmdailytrips__route_type__iexact='outbound')),
    )

    mileage_dict = {m['unit__code']: m['mileage'] for m in EKSTMMileage.objects.filter(date=selected_date).values('unit__code', 'mileage')}
    prev_mileage_dict = {m['unit__code']: m['mileage'] for m in EKSTMMileage.objects.filter(date=previous_date).values('unit__code', 'mileage')}
    three_day_mileage_dict = {m['unit__code']: m['mileage'] for m in EKSTMMileage.objects.filter(date=three_days_ago).values('unit__code', 'mileage')}

    unit_list = []
    low_usage_today = []
    not_used_units = []
    exceeds_units = []
    less_usage_units = []

    for unit in units:
        unit.count = unit.count or 0
        unit.inbound_count = unit.inbound_count or 0
        unit.outbound_count = unit.outbound_count or 0

        today_km_str = mileage_dict.get(unit.code)
        unit.mileage = today_km_str or "0 Km"

        prev_km_str = prev_mileage_dict.get(unit.code)
        if today_km_str and prev_km_str:
            try:
                today_km = float(today_km_str.replace('km', '').strip())
                prev_km = float(prev_km_str.replace('km', '').strip())
                daily_km = today_km - prev_km
                unit.daily_mileage = f"{int(daily_km)} Km"
                if daily_km < 10:
                    low_usage_today.append({'bus': unit.code, 'daily_mileage': f"{int(daily_km)} Km"})
            except (ValueError, TypeError):
                unit.daily_mileage = 'N/A'
        else:
            unit.daily_mileage = 'N/A'

        first_day = EKSTMMileage.objects.filter(unit__code=unit.code, date=current_month_start).values('mileage').first()
        if first_day and today_km_str:
            try:
                first_km = float(first_day['mileage'].replace('km', '').strip())
                today_km = float(today_km_str.replace('km', '').strip())
                monthly_val = int(today_km - first_km)
                unit.current_month_mileage = f"{monthly_val} Km"
                unit.card_bg = "" if monthly_val < 6000 else ("bg-yellow-200" if monthly_val < 7000 else "bg-red-200")
            except (ValueError, TypeError):
                unit.current_month_mileage = 'N/A'
                unit.card_bg = ""
        else:
            unit.current_month_mileage = 'N/A'
            unit.card_bg = ""

        three_day_str = three_day_mileage_dict.get(unit.code)
        if today_km_str and three_day_str:
            try:
                if float(today_km_str.replace('km', '').strip()) - float(three_day_str.replace('km', '').strip()) < 25:
                    not_used_units.append({'bus': unit.code})
            except Exception:
                pass

        if unit.current_month_mileage != 'N/A':
            try:
                m_val = int(unit.current_month_mileage.replace('Km', '').strip())
                if m_val > 7000:
                    exceeds_units.append({'bus': unit.code, 'mileage': m_val})
                if m_val < 1500:
                    less_usage_units.append({'bus': unit.code, 'mileage': m_val})
            except Exception:
                pass

        unit_list.append(unit)

    total_trips = EKSTMDailyTrips.objects.filter(ride_date=selected_date).count()
    monthly_trips = EKSTMDailyTrips.objects.filter(ride_date__gte=current_month_start, ride_date__lte=selected_date).count()

    salik = EKSTMSalik.objects.filter(salik_start_date=selected_date)
    monthly_salik = EKSTMSalik.objects.filter(salik_start_date__gte=current_month_start, salik_start_date__lte=selected_date)
    live_salik = salik.filter(Q(routetype__iexact='inbound') | Q(routetype__iexact='outbound'))
    dead_salik = salik.filter(routetype='')

    def salik_cost(qs):
        return f"{int(qs.aggregate(t=Sum(Cast('crossing_rate', IntegerField())))['t'] or 0)} Aed"

    return render(request, 'duty/ekstm_47seater_report_dashboard.html', {
        'selected_date': selected_date,
        'total_trips': total_trips,
        'monthly_trips': monthly_trips,
        'inbound_trips': EKSTMDailyTrips.objects.filter(ride_date=selected_date, route_type__iexact='inbound').count(),
        'outbound_trips': EKSTMDailyTrips.objects.filter(ride_date=selected_date, route_type__iexact='outbound').count(),
        'route_group_counts': EKSTMDailyTrips.objects.filter(ride_date=selected_date).values('route_group').annotate(count=Count('route_group')).order_by('route_group'),
        'unit_counts': unit_list,
        'total_salik_count': salik.count(),
        'monthly_salik_count': monthly_salik.count(),
        'total_salik_cost': salik_cost(salik),
        'monthly_salik_cost': salik_cost(monthly_salik),
        'live_salik_count': live_salik.count(),
        'live_salik_cost': salik_cost(live_salik),
        'dead_salik_count': dead_salik.count(),
        'dead_salik_cost': salik_cost(dead_salik),
        'not_used_count': len(not_used_units),
        'exceeds_count': len(exceeds_units),
        'less_usage_count': len(less_usage_units),
        'not_used_units': not_used_units,
        'exceeds_units': exceeds_units,
        'less_usage_units': less_usage_units,
        'low_usage_today_count': len(low_usage_today),
        'low_usage_today_units': low_usage_today,
    })
