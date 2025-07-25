from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.db import models
from .forms import MissingPersonForm
from .models import MissingPerson, CaseUpdate
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

    # Calculate statistics - matching template variable names
    total_cases = user_cases.count()
    active_cases = user_cases.filter(status__in=['pending', 'investigation']).count()
    resolved_cases = user_cases.filter(status__in=['found', 'closed']).count()

    # Get the 5 most recent reports
    recent_cases = user_cases.order_by('-created_at')[:5]

    context = {
        'total_cases': total_cases,
        'active_cases': active_cases,
        'resolved_cases': resolved_cases,
        'recent_cases': recent_cases,
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
    """Handle the submission of a new missing person report."""
    logger.info(f"Missing person report form accessed by user: {request.user}")
    
    if request.method == 'POST':
        form = MissingPersonForm(request.POST, request.FILES)
        logger.info(f"Form submitted by user: {request.user}")
        
        if form.is_valid():
            try:
                # Save the missing person record
                missing_person = form.save(commit=False)
                missing_person.reporter = request.user
                missing_person.save()
                
                logger.info(f"Successfully created missing person report with case number: {missing_person.case_number}")
                
                # Create initial case update
                CaseUpdate.objects.create(
                    case=missing_person,
                    description=f"Case reported by {request.user.get_full_name() or request.user.username}",
                    created_by=request.user
                )
                
                messages.success(
                    request,
                    f'Missing person report submitted successfully. Your case number is: {missing_person.case_number}'
                )
                messages.info(
                    request,
                    'You can track your case status using the case number provided.',
                    extra_tags='safe'
                )
                
                return redirect('track_cases')
                
            except Exception as e:
                logger.error(f"Error creating missing person report: {str(e)}", exc_info=True)
                messages.error(
                    request,
                    'An error occurred while submitting the report. Please try again or contact support if the problem persists.'
                )
        else:
            logger.warning(f"Form validation errors: {form.errors}")
            messages.error(request, 'Please correct the errors in the form.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = MissingPersonForm()
    
    return render(request, 'report_missing_person.html', {
        'form': form,
        'page_title': 'Report Missing Person',
    })

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

@login_required
def missing_person_detail(request, case_number):
    try:
        missing_person = MissingPerson.objects.get(case_number=case_number)
        # Check if user is authorized to view this report
        if not (request.user.is_admin() or request.user.is_officer() or missing_person.reporter == request.user):
            messages.error(request, 'You are not authorized to view this report.')
            return redirect('user_dashboard')
        
        # Fetch all updates related to this case
        all_updates = []
        # Add initial case creation update
        all_updates.append({
            'datetime': missing_person.created_at,
            'description': f'Case reported by {request.user.get_full_name() or request.user.username}'
        })
        
        # Add user updates
        for update in missing_person.updates.all():
            all_updates.append({
                'datetime': update.created_at,
                'description': update.description
            })
        
        # Add officer updates
        for update in missing_person.officer_updates.all():
            all_updates.append({
                'datetime': update.updated_at,
                'description': f'Officer Update: {update.description}'
            })
        
        # Sort all updates chronologically (most recent first)
        all_updates.sort(key=lambda x: x['datetime'], reverse=True)
        
        # Format for template
        formatted_updates = [
            {'date': u['datetime'].strftime('%B %d, %Y'), 'description': u['description']}
            for u in all_updates
        ]
        
        return render(request, 'missing_person_detail.html', {
            'missing_person': missing_person,
            'updates': formatted_updates
        })
    except MissingPerson.DoesNotExist:
        messages.error(request, 'Missing person report not found.')
        return redirect('user_dashboard')

@login_required
def feedback(request):
    """
    Displays the feedback form for users to submit their feedback.
    """
    from .models import Feedback
    if request.method == 'POST':
        title = request.POST.get('subject')
        description = request.POST.get('message')
        rating = request.POST.get('rating', '0')
        
        if title and description:
            try:
                feedback = Feedback.objects.create(
                    user=request.user,
                    title=title,
                    description=description,
                    rating=int(rating) if rating.isdigit() else 0
                )
                messages.success(request, 'Feedback submitted successfully! Thank you for your input.')
                return redirect('feedback')
            except Exception as e:
                logger.error(f"Error saving feedback: {str(e)}")
                messages.error(request, 'An error occurred while submitting your feedback. Please try again.')
        else:
            messages.error(request, 'Please fill out all required fields.')
    
    return render(request, 'feedback.html')
