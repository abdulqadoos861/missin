from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.db import models
from .forms import MissingPersonForm
from .models import MissingPerson
import logging
import json
from django.db import connection
from django.contrib.auth import update_session_auth_hash

logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def user_dashboard(request):
    """
    Displays the user's dashboard with statistics and recent reports.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    # Get all cases reported by the current user
    user_cases = MissingPerson.objects.filter(reporter=request.user)

    # Calculate statistics
    total_reports = user_cases.count()
    pending_reports = user_cases.filter(status__in=['pending', 'investigation']).count()
    solved_reports = user_cases.filter(status__in=['found', 'closed']).count()

    # Get the 5 most recent reports
    recent_reports = user_cases.order_by('-created_at')[:5]

    context = {
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'solved_reports': solved_reports,
        'recent_reports': recent_reports,
    }

    return render(request, 'userdashboard.html', context)

def report_missing_persons(request):
    return render(request, 'report_missing_person.html')

@login_required
def track_cases(request):
    logger.info(f"Track cases view accessed by user: {request.user}")
    try:
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to view your cases.')
            return redirect('login')

        # Use prefetch_related to efficiently fetch all related updates for all cases
        cases = MissingPerson.objects.filter(
            reporter_id=request.user.id
        ).prefetch_related(
            'updates', 'officer_updates'
        ).order_by('-created_at')

        total_cases = cases.count()
        active_cases = cases.filter(status__in=['pending', 'under_investigation']).count()
        resolved_cases = cases.filter(status__in=['found', 'closed']).count()

        processed_cases = []
        for case in cases:
            all_updates = []

            # Add initial case creation update
            all_updates.append({
                'datetime': case.created_at,
                'description': f'Case reported by {request.user.get_full_name()}'
            })

            # Add user updates (already prefetched)
            for update in case.updates.all():
                all_updates.append({
                    'datetime': update.created_at,
                    'description': update.description
                })

            # Add officer updates (already prefetched)
            for update in case.officer_updates.all():
                all_updates.append({
                    'datetime': update.updated_at,
                    'description': f'Officer Update: {update.description}'
                })
            
            # Sort all updates chronologically
            all_updates.sort(key=lambda x: x['datetime'], reverse=True)

            # Format for template
            formatted_updates = [
                {'date': u['datetime'].strftime('%B %d, %Y'), 'description': u['description']}
                for u in all_updates
            ]

            processed_cases.append({'case': case, 'updates': formatted_updates})

        context = {
            'cases': processed_cases,
            'total_cases': total_cases,
            'active_cases': active_cases,
            'resolved_cases': resolved_cases,
        }
        
        return render(request, 'user_track_cases.html', context)
    except Exception as e:
        logger.error(f"Unexpected error in track_cases view: {str(e)}", exc_info=True)
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return render(request, 'user_track_cases.html', {
            'cases': [], 'total_cases': 0, 'active_cases': 0, 'resolved_cases': 0,
        })

@login_required
@ensure_csrf_cookie
def report_missing_person(request):
    if request.method == 'POST':
        form = MissingPersonForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                missing_person = form.save(user=request.user)
                messages.success(request, f'Missing person report submitted successfully. Case number: {missing_person.case_number}')
                # Add a success message with a link to track the case
                messages.info(request, '<a href="/user/track-cases/" class="alert-link">Click here to track your case</a>')
                return redirect('track_cases')
            except Exception as e:
                logger.error(f"Error submitting missing person report: {str(e)}")
                messages.error(request, 'An error occurred while submitting the report. Please try again.')
        else:
            logger.error(f"Form validation errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = MissingPersonForm()
    
    return render(request, 'report_missing_person.html', {'form': form})

@login_required
def missing_person_detail(request, case_number):
    try:
        missing_person = MissingPerson.objects.get(case_number=case_number)
        # Check if user is authorized to view this report
        if not (request.user.is_admin() or request.user.is_officer() or missing_person.reporter == request.user):
            messages.error(request, 'You are not authorized to view this report.')
            return redirect('user_dashboard')
        return render(request, 'missing_person_detail.html', {'missing_person': missing_person})
    except MissingPerson.DoesNotExist:
        messages.error(request, 'Missing person report not found.')
        return redirect('user_dashboard')

@login_required
def my_reports(request):
    # Redirect to track_cases view which shows the user's reports
    return track_cases(request)

@login_required
def user_profile(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'password_change':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match')
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password updated successfully')
                
        elif form_type == 'notifications':
            # Handle notification preferences
            email_notifications = request.POST.get('email_notifications') == 'on'
            sms_notifications = request.POST.get('sms_notifications') == 'on'
            case_updates = request.POST.get('case_updates') == 'on'
            
            # Save notification preferences
            # Add your notification preferences saving logic here
            messages.success(request, 'Notification preferences updated successfully')
            
        elif form_type == 'privacy':
            # Handle privacy settings
            profile_visibility = request.POST.get('profile_visibility') == 'on'
            case_visibility = request.POST.get('case_visibility') == 'on'
            
            # Save privacy settings
            # Add your privacy settings saving logic here
            messages.success(request, 'Privacy settings updated successfully')
            
        else:
            # Handle profile update
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save()
            
            messages.success(request, 'Profile updated successfully')
            
    return render(request, 'user_profile.html')
