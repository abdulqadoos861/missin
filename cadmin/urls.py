from django.urls import path
from . import views

app_name = 'cadmin'

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('edit-officer/<int:officer_id>/', views.edit_officer, name='edit_officer'),
    path('delete-officer/<int:officer_id>/', views.delete_officer, name='delete_officer'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('register-officer/', views.register_officer, name='register_officer'),
    path('settings/', views.admin_settings, name='admin_settings'),
    path('settings/update-profile/', views.update_admin_profile, name='update_admin_profile'),
    path('settings/change-password/', views.change_admin_password, name='change_admin_password'),
    path('logout/', views.logout_view, name='logout'),
    path('contact-messages/', views.view_contact_messages, name='view_contact_messages'),
    path('reply-message/<int:message_id>/', views.reply_to_message, name='reply_to_message'),
    path('delete-message/<int:message_id>/', views.delete_message, name='delete_message'),
    path('feedback/', views.admin_feedback, name='admin_feedback'),
    path('reply-feedback/<int:feedback_id>/', views.reply_feedback, name='reply_feedback'),
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path('manage-cases/', views.case_list, name='manage_cases'),
    path('case-details/<int:case_id>/', views.case_detail, name='admin_case_details'),
    path('update-case-status/<int:case_id>/', views.case_update, name='update_case_status'),
]
