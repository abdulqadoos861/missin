from django.urls import path
from . import views
from django.shortcuts import redirect

def redirect_to_dashboard(request):
    return redirect('officer_dashboard')

urlpatterns = [
    path('', redirect_to_dashboard, name='officer_home'),
    path('officer-dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('view-cases/', views.view_cases, name='view_cases'),
    path('update-case/', views.update_case, name='update_case'),
    path('profile/', views.officer_profile, name='officer_profile'),
]

