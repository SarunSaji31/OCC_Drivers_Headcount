from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from .models import DriverImportLog

def user_in_driverimportlog_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        staff_id = request.user.username  # Assuming the username is the staff_id
        if DriverImportLog.objects.filter(staff_id=staff_id).exists():
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view