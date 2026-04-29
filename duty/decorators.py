from functools import wraps

from django.shortcuts import render

from .models import DriverImportLog


def admin_required(view_func):
    """Allow Django staff/superusers through; block regular drivers."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        if DriverImportLog.objects.filter(staff_id=request.user.username).exists():
            return render(request, 'duty/access_denied.html')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Backward-compatible alias kept so any external references don't break.
user_in_driverimportlog_required = admin_required
