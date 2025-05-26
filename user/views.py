from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from .forms import MissingPersonForm
from .models import MissingPerson, CaseUpdate
import logging
from django.db import connection
from django.contrib.auth import update_session_auth_hash

logger = logging.getLogger(__name__)

# Create your views here.

# @login_required
def user_dashboard(request):
    return render(request, 'userdashboard.html')

def report_missing_persons(request):
    return render(request, 'report_missing_person.html')

@login_required
def track_cases(request):
    logger.info(f"Track cases view accessed by user: {request.user}")
    try:
        # Verify user is authenticated
        if not request.user.is_authenticated:
            logger.error("User not authenticated")
            messages.error(request, 'Please log in to view your cases.')
            return redirect('login')

        # Get all cases reported by the current user using user.id
        try:
            # Log the SQL query
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM user_missingperson 
                    WHERE reporter_id = %s
                """, [request.user.id])
                count = cursor.fetchone()[0]
                logger.info(f"Raw SQL count of cases for user {request.user.id}: {count}")

            # Use user.id to filter cases
            cases = MissingPerson.objects.filter(reporter_id=request.user.id).order_by('-created_at')
            logger.info(f"Found {cases.count()} cases for user {request.user.id}")
            
            # Log case details for debugging
            for case in cases:
                logger.info(f"Case details - Number: {case.case_number}, Status: {case.status}, Created: {case.created_at}")
                logger.info(f"Case photo URL: {case.photo.url if case.photo else 'No photo'}")
        except Exception as e:
            logger.error(f"Database error while fetching cases: {str(e)}", exc_info=True)
            messages.error(request, 'Database error while fetching cases.')
            return render(request, 'user_track_cases.html', {
                'cases': [],
                'total_cases': 0,
                'active_cases': 0,
                'resolved_cases': 0,
            })
        
        # Calculate statistics using user.id
        try:
            total_cases = cases.count()
            active_cases = cases.filter(status__in=['pending', 'under_investigation']).count()
            resolved_cases = cases.filter(status__in=['found', 'closed']).count()
            logger.info(f"Statistics calculated - Total: {total_cases}, Active: {active_cases}, Resolved: {resolved_cases}")
        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}", exc_info=True)
            total_cases = 0
            active_cases = 0
            resolved_cases = 0
        
        # Process each case to include updates
        processed_cases = []
        for case in cases:
            try:
                # Initialize updates list
                case_updates = []
                
                # Add initial case creation update
                case_updates.append({
                    'date': case.created_at.strftime('%B %d, %Y'),
                    'description': f'Case reported by {request.user.get_full_name()}'
                })
                
                # Add user updates
                try:
                    user_updates = CaseUpdate.objects.filter(case_id=case.id)
                    logger.info(f"Found {user_updates.count()} user updates for case {case.case_number}")
                    for update in user_updates:
                        logger.info(f"User update for case {case.case_number}: {update.description}")
                        case_updates.append({
                            'date': update.created_at.strftime('%B %d, %Y'),
                            'description': update.description
                        })
                except Exception as e:
                    logger.error(f"Error fetching user updates for case {case.case_number}: {str(e)}", exc_info=True)
                    messages.warning(request, f'Could not load some updates for case {case.case_number}')
                
                # Add officer updates
                try:
                    officer_updates = case.officer_updates.all()
                    logger.info(f"Found {officer_updates.count()} officer updates for case {case.case_number}")
                    for update in officer_updates:
                        logger.info(f"Officer update for case {case.case_number}: {update.description}")
                        case_updates.append({
                            'date': update.created_at.strftime('%B %d, %Y'),
                            'description': f'Officer Update: {update.description}'
                        })
                except Exception as e:
                    logger.error(f"Error fetching officer updates for case {case.case_number}: {str(e)}", exc_info=True)
                    messages.warning(request, f'Could not load some officer updates for case {case.case_number}')
                
                # Sort updates by date
                case_updates.sort(key=lambda x: x['date'], reverse=True)
                
                # Create a dictionary with case data and updates
                case_data = {
                    'case': case,
                    'updates': case_updates
                }
                processed_cases.append(case_data)
                logger.info(f"Total updates for case {case.case_number}: {len(case_updates)}")
            except Exception as e:
                logger.error(f"Error processing case {case.case_number}: {str(e)}", exc_info=True)
                messages.warning(request, f'Could not process case {case.case_number}')
                continue
        
        context = {
            'cases': processed_cases,
            'total_cases': total_cases,
            'active_cases': active_cases,
            'resolved_cases': resolved_cases,
        }
        
        # Log context data for debugging
        logger.info(f"Context data - Total cases: {total_cases}, Active: {active_cases}, Resolved: {resolved_cases}")
        logger.info(f"Number of cases in context: {len(processed_cases)}")
        
        return render(request, 'user_track_cases.html', context)
    except Exception as e:
        logger.error(f"Unexpected error in track_cases view: {str(e)}", exc_info=True)
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return render(request, 'user_track_cases.html', {
            'cases': [],
            'total_cases': 0,
            'active_cases': 0,
            'resolved_cases': 0,
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
    reports = MissingPerson.objects.filter(reporter=request.user).order_by('-created_at')
    return render(request, 'user/my_reports.html', {'reports': reports})

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
