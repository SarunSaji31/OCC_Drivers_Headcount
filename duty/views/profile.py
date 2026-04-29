import logging

import requests

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from ..forms import DriverProfileForm
from ..models import DriverImportLog, DriverProfile
from ..utils import get_drive_file_url, upload_file_to_drive

logger = logging.getLogger(__name__)

_FILE_FIELDS = [
    ('profile_picture', 'picture'),
    ('license_front_file', 'license_front_file_id'),
    ('license_back_file', 'license_back_file_id'),
    ('eid_front_file', 'eid_front_file_id'),
    ('eid_back_file', 'eid_back_file_id'),
    ('passport_front_file', 'passport_front_file_id'),
    ('passport_back_file', 'passport_back_file_id'),
]

_SECTION_FIELD_MAP = {
    'profile_picture': [('profile_picture', 'picture')],
    'license': [('license_front_file', 'license_front_file_id'), ('license_back_file', 'license_back_file_id')],
    'eid': [('eid_front_file', 'eid_front_file_id'), ('eid_back_file', 'eid_back_file_id')],
    'passport': [('passport_front_file', 'passport_front_file_id'), ('passport_back_file', 'passport_back_file_id')],
}


@login_required
def user_profile(request):
    driver, _ = DriverImportLog.objects.get_or_create(
        staff_id=request.user.username,
        defaults={'driver_name': request.user.get_full_name() or request.user.username},
    )
    profile, _ = DriverProfile.objects.get_or_create(driver=driver)
    code = request.GET.get('code')

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        section = request.POST.get('section')
        code = request.POST.get('code') or code

        for file_field, id_field in _SECTION_FIELD_MAP.get(section, []):
            upload = request.FILES.get(file_field)
            if upload:
                file_id, auth_url = upload_file_to_drive(upload, f"{driver.staff_id}_{section}_{upload.name}", code)
                if auth_url:
                    return JsonResponse({'redirect': auth_url})
                setattr(profile, id_field, file_id)

        profile.save()
        response_data = {'success': True}
        if section == 'profile_picture' and profile.picture:
            response_data['picture_url'] = get_drive_file_url(profile.picture)
        return JsonResponse(response_data)

    if request.method == 'POST':
        form = DriverProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            for field_name, id_field in _FILE_FIELDS:
                file = request.FILES.get(field_name)
                if file:
                    file_id, auth_url = upload_file_to_drive(file, f"{driver.staff_id}_{field_name}_{file.name}", code)
                    if auth_url:
                        return redirect(auth_url)
                    setattr(profile, id_field, file_id)
            profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('user_profile')
        messages.error(request, "Please correct the errors below.")
    else:
        form = DriverProfileForm(instance=profile)

    return render(request, 'duty/user_profile.html', {
        'driver': driver,
        'form': form,
        'profile': profile,
        'picture_url': get_drive_file_url(profile.picture) if profile.picture else None,
    })


@login_required
def oauth2callback(request):
    code = request.GET.get('code')
    if code:
        return redirect(f"{reverse('user_profile')}?code={code}")
    return redirect('user_profile')


@login_required
def drive_image_proxy(request, file_id):
    if not file_id:
        raise Http404("Missing file ID")
    url = f"https://docs.google.com/uc?export=download&id={file_id}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception:
        raise Http404("Could not fetch image")
    return HttpResponse(r.content, content_type=r.headers.get('Content-Type', 'application/octet-stream'))
