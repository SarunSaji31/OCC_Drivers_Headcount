from django.shortcuts import render, redirect
from .forms import DriverForm, TripFormSet
from .models import Driver
from django.http import JsonResponse

def home(request):
    return render(request, 'duty/home.html')

def enter_head_count(request):
    if request.method == 'POST':
        driver_form = DriverForm(request.POST)
        trip_formset = TripFormSet(request.POST)

        if driver_form.is_valid() and trip_formset.is_valid():
            driver = driver_form.save()
            trips = trip_formset.save(commit=False)
            for trip in trips:
                trip.driver = driver
                trip.save()
            return redirect('success')
        else:
            driver_form_errors = driver_form.errors
            trip_formset_errors = [form.errors for form in trip_formset if form.errors]

    else:
        driver_form = DriverForm()
        trip_formset = TripFormSet()
        driver_form_errors = None
        trip_formset_errors = None

    return render(request, 'duty/enter_head_count.html', {
        'driver_form': driver_form,
        'trip_formset': trip_formset,
        'driver_form_errors': driver_form_errors,
        'trip_formset_errors': trip_formset_errors,
    })

def success(request):
    return render(request, 'duty/success.html')

def driver_autocomplete(request):
    if 'term' in request.GET:
        qs = Driver.objects.filter(driver_name__icontains=request.GET.get('term'))
        names = list()
        for driver in qs:
            names.append(driver.driver_name)
        return JsonResponse(names, safe=False)
    return render(request, 'duty/enter_head_count.html')

def staff_id_autocomplete(request):
    if 'term' in request.GET:
        qs = Driver.objects.filter(staff_id__icontains(request.GET.get('term')))
        staff_ids = list()
        for driver in qs:
            staff_ids.append(driver.staff_id)
        return JsonResponse(staff_ids, safe=False)
    return render(request, 'duty/enter_head_count.html')

def get_driver_name(request):
    staff_id = request.GET.get('staff_id', None)
    if staff_id:
        try:
            driver = Driver.objects.get(staff_id=staff_id)
            return JsonResponse({'driver_name': driver.driver_name})
        except Driver.DoesNotExist:
            return JsonResponse({'driver_name': ''})
    return JsonResponse({'driver_name': ''})
