from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import DriverTripForm
from .models import DriverTrip, DriverImportLog

def home(request):
    return render(request, 'duty/home.html')

def enter_head_count(request):
    if request.method == 'POST':
        form = DriverTripForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('success')
        else:
            form_errors = form.errors
    else:
        form = DriverTripForm()
        form_errors = None

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
        try:
            driver_log = DriverImportLog.objects.filter(staff_id=staff_id).first()
            if driver_log:
                return JsonResponse({'driver_name': driver_log.driver_name})
            else:
                return JsonResponse({'driver_name': ''})
        except DriverImportLog.DoesNotExist:
            return JsonResponse({'driver_name': ''})
    return JsonResponse({'driver_name': ''})
