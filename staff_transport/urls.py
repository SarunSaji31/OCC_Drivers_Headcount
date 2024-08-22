from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

def test_view(request):
    return HttpResponse("The application is running.")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', test_view),  # This is a simple test view to check if the app is running
    path('duty/', include('duty.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
