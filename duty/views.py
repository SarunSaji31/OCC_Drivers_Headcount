from django.shortcuts import render, redirect
from .forms import DutyCardForm

def home(request):
    return render(request, 'duty/home.html')

def enter_head_count(request):
    if request.method == 'POST':
        form = DutyCardForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('success')
    else:
        form = DutyCardForm()
    return render(request, 'duty/enter_head_count.html', {'form': form})

def success(request):
    return render(request, 'duty/success.html')
