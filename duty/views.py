from django.shortcuts import render, redirect
from .forms import DriverForm, TripFormSet

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
