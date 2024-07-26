from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('enter_head_count/', views.enter_head_count, name='enter_head_count'),
    path('success/', views.success, name='success'),
]
