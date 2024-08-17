from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from .forms import DriverTripFormSet
from .models import DriverTrip, DriverImportLog, DutyCardTrip
import pandas as pd

def home(request):
    return render(request, 'duty/home.html')

def enter_head_count(request):
    if request.method == 'POST':
        # Initialize the formset with POST data
        trip_formset = DriverTripFormSet(request.POST, prefix='drivertrip_set')

        try:
            if trip_formset.is_valid():
                staff_id = request.POST.get('staff_id')
                driver_name = request.POST.get('driver_name')
                duty_card_no = request.POST.get('duty_card_no')

                for form in trip_formset:
                    if form.is_valid():
                        trip_date = form.cleaned_data.get('date')
                        route_name = form.cleaned_data.get('route_name')

                        # Check if a DriverTrip with the same staff_id, duty_card_no, and date already exists
                        existing_trip = DriverTrip.objects.filter(
                            staff_id=staff_id,
                            duty_card_no=duty_card_no,
                            date=trip_date,
                            route_name=route_name
                        ).exists()

                        if existing_trip:
                            form.add_error(None, f"Data for Staff ID {staff_id}, Duty Card No {duty_card_no} on {trip_date} already exists.")
                        else:
                            # Create and save the trip record
                            DriverTrip.objects.create(
                                staff_id=staff_id,
                                driver_name=driver_name,
                                duty_card_no=duty_card_no,
                                route_name=route_name,
                                pick_up_time=form.cleaned_data.get('pick_up_time'),
                                drop_off_time=form.cleaned_data.get('drop_off_time'),
                                shift_time=form.cleaned_data.get('shift_time'),
                                date=trip_date,
                                head_count=form.cleaned_data.get('head_count'),
                                trip_type=form.cleaned_data.get('trip_type')
                            )
                return redirect('success')
            else:
                print("Formset is not valid")
                print(trip_formset.errors)
                return render(request, 'duty/enter_head_count.html', {
                    'trip_formset': trip_formset,
                })

        except Exception as e:
            print("An error occurred:", str(e))
            return render(request, 'duty/enter_head_count.html', {
                'trip_formset': trip_formset,
                'error_message': f"An error occurred: {str(e)}"
            })
    else:
        trip_formset = DriverTripFormSet(prefix='drivertrip_set')

    return render(request, 'duty/enter_head_count.html', {
        'trip_formset': trip_formset,
    })

def success(request):
    return render(request, 'duty/success.html')

def report_view(request):
    date_filter = request.GET.get('date')
    if date_filter:
        driver_trips = DriverTrip.objects.filter(date=date_filter)
    else:
        driver_trips = DriverTrip.objects.all()

    context = {
        'driver_trips': driver_trips,
    }
    return render(request, 'duty/report_data.html', context)

def download_report(request):
    date_filter = request.GET.get('date')
    if date_filter:
        driver_trips = DriverTrip.objects.filter(date=date_filter)
    else:
        driver_trips = DriverTrip.objects.all()

    # Prepare data for the Excel file
    data = []
    for trip in driver_trips:
        data.append({
            'Staff ID': trip.staff_id,
            'Driver Name': trip.driver_name,
            'Duty Card No': trip.duty_card_no,
            'Route Name': trip.route_name,
            'Pick Up Time': trip.pick_up_time.strftime("%H:%M"),
            'Drop Off Time': trip.drop_off_time.strftime("%H:%M"),
            'Shift Time': trip.shift_time.strftime("%H:%M"),
            'Trip Type': trip.trip_type,
            'Date': trip.date.strftime("%Y-%m-%d"),
            'Head Count': trip.head_count,
        })

    df = pd.DataFrame(data)

    # Create an HttpResponse object with the appropriate Excel header
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=driver_trip_report_{date_filter}.xlsx'

    # Use Pandas to write the DataFrame to the response as an Excel file
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
        duty_card_no = request.GET['duty_card_no']
        trips = DutyCardTrip.objects.filter(duty_card_no=duty_card_no)
        trip_details = list(trips.values('route_name', 'pick_up_time', 'drop_off_time', 'shift_time', 'trip_type'))

        # Format the time fields
        for trip in trip_details:
            trip['pick_up_time'] = trip['pick_up_time'].strftime("%H:%M")
            trip['drop_off_time'] = trip['drop_off_time'].strftime("%H:%M")
            trip['shift_time'] = trip['shift_time'].strftime("%H:%M")
            trip['trip_type'] = trip['trip_type']  

            print(trip)

        return JsonResponse({'trips': trip_details}, safe=False)
    
    return JsonResponse({'trips': []}, safe=False)
