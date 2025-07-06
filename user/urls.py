from django.urls import path
from django.shortcuts import redirect, reverse
from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView
from django.http import HttpResponseRedirect
from . import views
from frontend.views import login_view
from .test_email import TestEmailView

def custom_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('login'))

def redirect_to_dashboard(request):
    return redirect('user_dashboard')

urlpatterns = [
    path('', redirect_to_dashboard, name='user_home'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('report-missing-person/', views.report_missing_person, name='report_missing_person'),
    path('missing-person/<str:case_number>/', views.missing_person_detail, name='missing_person_detail'),
    path('my-reports/', views.track_cases, name='my_reports'),
    path('track-cases/', views.track_cases, name='track_cases'),
    path('profile/', views.user_profile, name='user_profile'),
    path('logout/', custom_logout, name='user_logout'),
    path('test-email/', TestEmailView.as_view(), name='test_email'),
]
