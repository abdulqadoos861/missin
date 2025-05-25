from django.urls import path
from django.shortcuts import redirect
from django.contrib.auth.views import LogoutView
from . import views
from frontend.views import login_view

def redirect_to_dashboard(request):
    return redirect('user_dashboard')

urlpatterns = [
    path('', redirect_to_dashboard, name='user_home'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('report-missing-person/', views.report_missing_person, name='report_missing_person'),
    path('missing-person/<str:case_number>/', views.missing_person_detail, name='missing_person_detail'),
    path('my-reports/', views.my_reports, name='my_reports'),
    path('track-cases/', views.track_cases, name='track_cases'),
    path('logout/', login_view, name='logout'),
]

