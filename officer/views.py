from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import re
from frontend.models import User
from user.models import MissingPerson, CaseUpdate
from officer.models import CaseEvidence
from user.models import Feedback
import logging

logger = logging.getLogger(__name__)

def is_officer(user):
    return user.user_type == 'officer'

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def officer_dashboard(request):
    try:
        # Get officer's assigned cases
        officer = request.user
        assigned_cases = MissingPerson.objects.filter(assigned_officer=officer)
        
        # Get case statistics
        total_cases = assigned_cases.count()
        pending_cases = assigned_cases.filter(status='pending').count()
        investigation_cases = assigned_cases.filter(status='investigation').count()
        found_cases = assigned_cases.filter(status='found').count()
        closed_cases = assigned_cases.filter(status='closed').count()
        
        # Calculate percentages
        pending_percentage = (pending_cases / total_cases * 100) if total_cases > 0 else 0
        investigation_percentage = (investigation_cases / total_cases * 100) if total_cases > 0 else 0
        found_percentage = (found_cases / total_cases * 100) if total_cases > 0 else 0
        
        # Get recent cases (last 5)
        recent_cases = assigned_cases.order_by('-created_at')[:5]
        
        context = {
            'total_cases': total_cases,
            'pending_cases': pending_cases,
            'investigation_cases': investigation_cases,
            'found_cases': found_cases,
            'closed_cases': closed_cases,
            'pending_percentage': pending_percentage,
            'investigation_percentage': investigation_percentage,
            'found_percentage': found_percentage,
            'recent_cases': recent_cases,
        }
        
        return render(request, 'officer_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in officer_dashboard view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while loading the dashboard: {str(e)}")
        return render(request, 'officer_dashboard.html', {
            'total_cases': 0,
            'pending_cases': 0,
            'investigation_cases': 0,
            'found_cases': 0,
            'closed_cases': 0,
            'pending_percentage': 0,
            'investigation_percentage': 0,
            'found_percentage': 0,
            'recent_cases': [],
        })

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def officer_view_case(request):
    try:
        officer = request.user
        cases = MissingPerson.objects.all()
        logger.debug(f"Officer: {officer.username}, Total cases found: {cases.count()}")
        
        # Get search query and filters
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        date_filter = request.GET.get('date', '')
        
        # By default, exclude closed cases unless specifically filtered
        if not status_filter:
            cases = cases.exclude(status='closed')
            logger.debug(f"Excluding closed cases by default: {cases.count()} cases")
        elif status_filter == 'all':
            # Show all cases including closed ones
            logger.debug("Showing all cases including closed")
        else:
            # Apply specific status filter
            cases = cases.filter(status=status_filter)
            logger.debug(f"After status filter '{status_filter}': {cases.count()} cases")
        
        # Apply filters
        if search_query:
            cases = cases.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(case_number__icontains=search_query)
            )
            logger.debug(f"After search filter '{search_query}': {cases.count()} cases")
        
        if date_filter:
            today = timezone.now()
            if date_filter == 'today':
                cases = cases.filter(last_seen_date__date=today.date())
            elif date_filter == 'week':
                week_ago = today - timedelta(days=7)
                cases = cases.filter(last_seen_date__gte=week_ago)
            elif date_filter == 'month':
                month_ago = today - timedelta(days=30)
                cases = cases.filter(last_seen_date__gte=month_ago)
            logger.debug(f"After date filter '{date_filter}': {cases.count()} cases")
        
        # Order by most recent first
        cases = cases.order_by('-created_at')
        
        # Get case statistics
        total_cases = cases.count()
        pending_cases = cases.filter(status='pending').count()
        investigation_cases = cases.filter(status='investigation').count()
        found_cases = cases.filter(status='found').count()
        closed_cases = cases.filter(status='closed').count()
        
        # Pagination
        paginator = Paginator(cases, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'date_filter': date_filter,
            'total_cases': total_cases,
            'pending_cases': pending_cases,
            'investigation_cases': investigation_cases,
            'found_cases': found_cases,
            'closed_cases': closed_cases,
        }
        
        logger.debug(f"Rendering officer_view_case with {total_cases} total cases for officer {officer.username}")
        return render(request, 'officer_view_case.html', context)
        
    except Exception as e:
        logger.error(f"Error in officer_view_case view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while retrieving cases: {str(e)}")
        return render(request, 'officer_view_case.html', {
            'page_obj': None,
            'total_cases': 0,
            'pending_cases': 0,
            'investigation_cases': 0,
            'found_cases': 0,
            'closed_cases': 0,
        })

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def officer_view_case_detail(request, case_number):
    try:
        # Get the case with all related data
        case = get_object_or_404(MissingPerson.objects.select_related(
            'reporter', 
            'assigned_officer'
        ).prefetch_related(
            'updates', 
            'evidence'
        ), case_number=case_number, assigned_officer=request.user)
        
        # Get case updates with related user data
        updates = case.updates.select_related('created_by').all()
        
        # Get case evidence
        evidence = case.evidence.all()
        
        context = {
            'case': case,
            'updates': updates,
            'evidence': evidence,
        }
        
        return render(request, 'officer_view_case_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in officer_view_case_detail view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while retrieving case details: {str(e)}")
        return redirect('officer:officer_dashboard')

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def officer_update_case(request, case_number):
    try:
        case = get_object_or_404(MissingPerson, case_number=case_number, assigned_officer=request.user)
        
        if request.method == 'POST':
            # Check if case is already closed
            if case.status == 'closed':
                messages.error(request, 'Cannot update a closed case.')
                return redirect('officer:officer_view_case_detail', case_number=case_number)
                
            new_status = request.POST.get('status')
            update_description = request.POST.get('description', '').strip()
            location_found = request.POST.get('location_found', '').strip()
            found_date = request.POST.get('found_date', '').strip()
            evidence_files = request.FILES.getlist('evidence_files')
            evidence_descriptions = request.POST.getlist('evidence_descriptions')
            
            # Validate status
            if not new_status or new_status not in dict(MissingPerson.STATUS_CHOICES):
                messages.error(request, 'Invalid status selected.')
                return redirect('officer:officer_update_case', case_number=case_number)
            
            # Store old status for comparison
            old_status = case.status
            
            # Validate status-specific requirements
            if new_status == 'found':
                if not location_found:
                    messages.error(request, 'Location found is required when marking case as found.')
                    return redirect('officer:officer_update_case', case_number=case_number)
                if not found_date:
                    messages.error(request, 'Found date is required when marking case as found.')
                    return redirect('officer:officer_update_case', case_number=case_number)
                
                # Update found information
                case.location_found = location_found
                case.found_date = found_date
                
            elif new_status == 'closed':
                closure_photo = request.FILES.get('closure_proof_photo')
                if not closure_photo:
                    messages.error(request, 'A closure proof photo is required to close the case.')
                    return redirect('officer:officer_update_case', case_number=case_number)
                case.closure_proof_photo = closure_photo
                
                if not update_description:
                    messages.error(request, 'Closure reason is required when closing a case.')
                    return redirect('officer:officer_update_case', case_number=case_number)
            
            # Update case status
            case.status = new_status
            case.save()
            
            # Create status update record
            status_update = CaseUpdate.objects.create(
                case=case,
                description=f"Status changed from {case.get_status_display(old_status)} to {case.get_status_display()}",
                created_by=request.user
            )
            
            # Add additional update if description provided
            if update_description:
                CaseUpdate.objects.create(
                    case=case,
                    description=update_description,
                    created_by=request.user
                )
            
            # Handle evidence uploads
            for i, file in enumerate(evidence_files):
                if i < len(evidence_descriptions):
                    description = evidence_descriptions[i].strip()
                else:
                    description = ""
                    
                evidence = CaseEvidence.objects.create(
                    case=case,
                    file=file,
                    description=description if description else f"Evidence uploaded on {timezone.now().strftime('%Y-%m-%d')}",
                    uploaded_by=request.user
                )
            
            # Send email notification to the reporter
            if case.reporter and case.reporter.email:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    f'Case Update: {case.case_number}',
                    f'Dear {case.reporter.get_full_name() or case.reporter.username},\n\n'
                    f'The status of case {case.case_number} regarding {case.first_name} {case.last_name} '
                    f'has been updated to {case.get_status_display()}.\n\n'
                    f'Description: {update_description if update_description else "No additional description provided."}\n\n'
                    f'Please log in to the portal for more details.\n\n'
                    f'Thank you,\nPakistani Police Force',
                    settings.DEFAULT_FROM_EMAIL,
                    [case.reporter.email],
                    fail_silently=True,
                )
                logger.info(f"Sent email notification to {case.reporter.email} for case {case.case_number}")

            messages.success(request, f'Case status has been updated to {case.get_status_display()}.')
            return redirect('officer:officer_view_case_detail', case_number=case_number)
            
    except Exception as e:
        logger.error(f"Error in officer_update_case view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while updating case: {str(e)}")
        return redirect('officer:officer_update_case', case_number=case_number)
    
    context = {
        'case': case,
    }
    return render(request, 'officer_update_case.html', context)

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def officer_profile(request):
    officer = request.user
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            address = request.POST.get('address', '').strip()
            
            # Validate required fields
            if not all([first_name, last_name, email, phone_number, address]):
                messages.error(request, 'All fields are required.')
                return redirect('officer:officer_profile')
            
            # Validate email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                messages.error(request, 'Please enter a valid email address.')
                return redirect('officer:officer_profile')
            
            # Check if email is already taken by another user
            if User.objects.exclude(id=officer.id).filter(email=email).exists():
                messages.error(request, 'This email is already registered to another user.')
                return redirect('officer:officer_profile')
            
            # Update officer information
            officer.first_name = first_name
            officer.last_name = last_name
            officer.email = email
            officer.phone_number = phone_number
            officer.address = address
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                officer.profile_picture = request.FILES['profile_picture']
            
            # Save changes
            officer.save(update_fields=[
                'first_name', 'last_name', 'email', 'phone_number',
                'address', 'profile_picture'
            ])
            
            messages.success(request, 'Profile updated successfully!')
            
        except Exception as e:
            logger.error(f"Error updating officer profile: {str(e)}", exc_info=True)
            messages.error(request, f"Error updating profile: {str(e)}")
    
    context = {
        'officer': officer,
    }
    return render(request, 'officer_profile.html', context)

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def officer_feedback(request):
    """Display all user feedback in the officer dashboard."""
    feedbacks = Feedback.objects.all().order_by('-created_at')
    paginator = Paginator(feedbacks, 15)  # Show 15 feedbacks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'feedbacks': page_obj,
    }
    return render(request, 'officer_feedback.html', context)

def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')
