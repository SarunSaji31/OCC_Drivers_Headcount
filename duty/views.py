from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import DriverForm, TripFormSet
from .models import Driver

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
        term = request.GET.get('term')
        qs = Driver.objects.filter(driver_name__icontains=term)
        names = list(qs.values_list('driver_name', flat=True))
        return JsonResponse(names, safe=False)
    return JsonResponse([], safe=False)

def staff_id_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
        qs = Driver.objects.filter(staff_id__icontains=term)
        staff_ids = list(qs.values_list('staff_id', flat=True))
        return JsonResponse(staff_ids, safe=False)
    return JsonResponse([], safe=False)

def get_driver_name(request):
    staff_id = request.GET.get('staff_id', None)
    if staff_id:
        try:
            driver = Driver.objects.filter(staff_id=staff_id).first()
            if driver:
                return JsonResponse({'driver_name': driver.driver_name})
            else:
                return JsonResponse({'driver_name': ''})
        except Driver.DoesNotExist:
            return JsonResponse({'driver_name': ''})
    return JsonResponse({'driver_name': ''})
