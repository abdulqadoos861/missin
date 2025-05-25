from django.urls import path
from django.shortcuts import redirect
from . import views

def redirect_to_dashboard(request):
    return redirect('admin_dashboard')

urlpatterns = [
    path('', redirect_to_dashboard, name='admin_home'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('register-officer/', views.register_officer, name='register_officer'),
    path('cases/', views.manage_cases, name='manage_cases'),
    path('case/<int:case_id>/', views.admin_case_details, name='admin_case_details'),
    path('case/<int:case_id>/assign-officer/', views.assign_officer, name='assign_officer'),
    path('case/<int:case_id>/update-status/', views.update_case_status, name='update_case_status'),
    path('case/<int:case_id>/add-update/', views.add_case_update, name='add_case_update'),
    path('manage-user/', views.manage_user, name='manage_user'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
]

