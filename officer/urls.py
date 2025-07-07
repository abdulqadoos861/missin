from django.urls import path
from . import views

app_name = 'officer'

urlpatterns = [
    path('', views.officer_dashboard, name='officer_home'),
    path('dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('view-cases/', views.officer_view_case, name='officer_view_case'),
    path('case-detail/<str:case_number>/', views.officer_view_case_detail, name='officer_view_case_detail'),
    path('update-case/<str:case_number>/', views.officer_update_case, name='officer_update_case'),
    path('profile/', views.officer_profile, name='officer_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('feedback/', views.officer_feedback, name='officer_feedback'),
]
