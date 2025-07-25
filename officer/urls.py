from django.urls import path
from . import views

app_name = 'officer'

urlpatterns = [
    path('', views.officer_dashboard, name='officer_home'),
    path('dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('profile/', views.officer_profile, name='officer_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('feedback/', views.officer_feedback, name='officer_feedback'),
]
