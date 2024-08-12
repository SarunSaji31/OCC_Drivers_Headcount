from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import DriverForm, DriverTripFormSet
from .models import DutyCardTrip, DriverImportLog, Driver

def home(request):
    return render(request, 'duty/home.html')

from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import DriverForm, DriverTripFormSet
from .models import Driver, DriverTrip, DriverImportLog, DutyCardTrip

def home(request):
    return render(request, 'duty/home.html')

def enter_head_count(request):
    if request.method == 'POST':
        driver_form = DriverForm(request.POST)
        trip_formset = DriverTripFormSet(request.POST)

        try:
            if driver_form.is_valid() and trip_formset.is_valid():
                staff_id = driver_form.cleaned_data.get('staff_id')

                # Fetch the existing driver or create a new one if it doesn't exist
                driver, created = Driver.objects.get_or_create(
                    staff_id=staff_id,
                    defaults={
                        'driver_name': driver_form.cleaned_data.get('driver_name'),
                        'duty_card_no': driver_form.cleaned_data.get('duty_card_no'),
                    }
                )

                # If the driver already exists, update the existing record
                if not created:
                    driver.driver_name = driver_form.cleaned_data.get('driver_name')
                    driver.duty_card_no = driver_form.cleaned_data.get('duty_card_no')
                    driver.save()

                # Bind each form in the formset to the driver instance and save
                trip_formset.instance = driver
                trip_formset.save()  # This will save all forms at once if valid
                return redirect('success')
            else:
                # Log form errors for debugging
                print("Driver Form Errors:", driver_form.errors)
                print("Trip Formset Errors:", trip_formset.errors)
        except Exception as e:
            print("An error occurred:", str(e))  # Debugging line

    else:
        driver_form = DriverForm()
        trip_formset = DriverTripFormSet()

    return render(request, 'duty/enter_head_count.html', {
        'driver_form': driver_form,
        'trip_formset': trip_formset,
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
    return JsonResponse([], safe=False)

def get_duty_card_details(request):
    if 'duty_card_no' in request.GET:
        duty_card_no = request.GET['duty_card_no']
        trips = DutyCardTrip.objects.filter(duty_card_no=duty_card_no)
        trip_details = list(trips.values('route_name', 'pick_up_time', 'drop_off_time'))
        return JsonResponse({'trips': trip_details}, safe=False)
    return JsonResponse({'trips': []}, safe=False)