import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from ..forms import CustomUserCreationForm, PasswordResetRequestForm, SetNewPasswordForm

logger = logging.getLogger(__name__)


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            logger.debug("Form is valid, saving user.")
            form.save()
            messages.success(request, 'Your account has been created successfully! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'There were errors in your form. Please fix them.')
            logger.warning("Form is not valid.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('login')


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            staff_id = form.cleaned_data['staff_id']
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(username=staff_id)
                if user.email == email:
                    # Mark this user as verified for the reset flow. Only a
                    # request that passed the staff_id + email check above may
                    # proceed to set_new_password.
                    request.session['password_reset_user_id'] = user.id
                    return redirect(reverse('set_new_password', args=[user.id]))
                else:
                    messages.error(request, 'The email address does not match our records.')
            except User.DoesNotExist:
                messages.error(request, 'No user found with that Staff ID.')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'registration/password_reset_request.html', {'form': form})


def set_new_password(request, user_id):
    # Only allow if this user_id was verified in password_reset_request.
    # Without this check any visitor could reset any account by guessing the id.
    if request.session.get('password_reset_user_id') != user_id:
        messages.error(request, 'Please verify your Staff ID and email before resetting your password.')
        return redirect('password_reset')

    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            user.password = make_password(form.cleaned_data['new_password'])
            user.save()
            # Consume the one-time verification so the link can't be reused.
            request.session.pop('password_reset_user_id', None)
            messages.success(request, 'Your password has been reset successfully.')
            return redirect('login')
    else:
        form = SetNewPasswordForm()
    return render(request, 'registration/set_new_password.html', {'form': form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if request.POST.get('remember_me'):
                    request.session.set_expiry(1209600)
                    request.session['remember_me'] = True
                else:
                    request.session.set_expiry(300)
                    request.session['remember_me'] = False
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})
