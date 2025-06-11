from django.urls import path
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from . import views

app_name = 'cadmin'  # Add this line for URL namespacing

def redirect_to_dashboard(request):
    return redirect('cadmin:admin_dashboard')

urlpatterns = [
    path('', redirect_to_dashboard, name='admin_home'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('register-officer/', views.register_officer, name='register_officer'),
    path('edit-officer/<int:officer_id>/', views.edit_officer, name='edit_officer'),
    path('cases/', views.manage_cases, name='manage_cases'),
    path('case/<int:case_id>/', views.admin_case_details, name='admin_case_details'),
    path('case/<int:case_id>/update-status/', views.update_case_status, name='update_case_status'),
    path('case/<int:case_id>/add-update/', views.add_case_update, name='add_case_update'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('settings/', views.admin_settings, name='admin_settings'),
    path('settings/update-profile/', views.update_admin_profile, name='update_admin_profile'),
    path('settings/change-password/', views.change_admin_password, name='change_admin_password'),
    path('contact-messages/', views.view_contact_messages, name='view_contact_messages'),
    path('reply-to-message/<int:message_id>/', views.reply_to_message, name='reply_to_message'),
    # Logout URL - Updated to use namespaced URL
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]

