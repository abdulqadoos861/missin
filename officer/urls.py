from django.urls import path
from . import views
from django.shortcuts import redirect

def redirect_to_dashboard(request):
    return redirect('officer_dashboard')

urlpatterns = [
    path('', redirect_to_dashboard, name='officer_home'),
    path('officer-dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('view-cases/', views.view_cases, name='officer_view_case'),
    path('view-cases/<int:case_id>/', views.view_case_detail, name='officer_view_case_detail'),
    path('update-case/<int:case_id>/', views.update_case, name='officer_update_case'),
    path('profile/', views.officer_profile, name='officer_profile'),
]

 