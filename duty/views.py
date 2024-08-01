from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import DriverTripForm
from .models import DutyCardTrip, DriverImportLog

def home(request):
    return render(request, 'duty/home.html')

def duty_card_no_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
        # Query and ensure unique duty card numbers using set to remove duplicates
        qs = DutyCardTrip.objects.filter(duty_card_no__icontains=term).values_list('duty_card_no', flat=True)
        duty_card_nos = list(set(qs))  # Convert to set and back to list for unique values
        return JsonResponse(duty_card_nos, safe=False)
    return JsonResponse([], safe=False)

def get_duty_card_details(request):
    if 'duty_card_no' in request.GET:
        duty_card_no = request.GET['duty_card_no']
        # Fetch related trip details
        trips = DutyCardTrip.objects.filter(duty_card_no=duty_card_no)
        trip_details = list(trips.values('route_name', 'pick_up_time', 'drop_off_time'))
        return JsonResponse({'trips': trip_details}, safe=False)
    return JsonResponse({'trips': []}, safe=False)

def enter_head_count(request):
    form_errors = None
    if request.method == 'POST':
        form = DriverTripForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('success')  # Ensure this redirect URL is correct
        else:
            form_errors = form.errors
    else:
        form = DriverTripForm()

    return render(request, 'duty/enter_head_count.html', {
        'form': form,
        'form_errors': form_errors,
    })

def success(request):
    return render(request, 'duty/success.html')

def driver_name_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
        qs = DriverImportLog.objects.filter(driver_name__icontains=term)
        names = list(qs.values_list('driver_name', flat=True))
        return JsonResponse(names, safe=False)
    return JsonResponse([], safe=False)

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
        # Fetch the driver name associated with the staff ID
        driver_log = DriverImportLog.objects.filter(staff_id=staff_id).first()
        if driver_log:
            return JsonResponse({'driver_name': driver_log.driver_name})
        else:
            return JsonResponse({'driver_name': ''})
    return JsonResponse({'driver_name': ''})
