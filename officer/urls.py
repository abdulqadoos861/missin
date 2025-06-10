from django.urls import path
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.conf import settings
from . import views

app_name = 'officer'

def redirect_to_dashboard(request):
    return redirect('officer:officer_dashboard')

urlpatterns = [
    path('', redirect_to_dashboard, name='officer_home'),
    path('officer-dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('view-cases/', views.view_cases, name='officer_view_case'),
    path('view-cases/<int:case_id>/', views.officer_view_case_detail, name='officer_view_case_detail'),
    path('case/<int:case_id>/add-update/', views.add_case_update, name='add_case_update'),
    path('case/<int:case_id>/update-status/', views.update_case_status, name='update_case_status'),
    path('profile/', views.officer_profile, name='officer_profile'),
    path('case/<int:case_id>/add-note/', views.add_case_note, name='add_case_note'),
    path('case/<int:case_id>/add-evidence/', views.add_case_evidence, name='add_case_evidence'),
    path('logout/', views.officer_logout, name='logout'),
]