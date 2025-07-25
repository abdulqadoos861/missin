from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import re
import logging

from frontend.models import User
from user.models import MissingPerson, Feedback

logger = logging.getLogger(__name__)

def is_officer(user):
    return user.user_type == 'officer'

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def officer_dashboard(request):
    try:
        # Get officer's basic info
        officer = request.user
        
        context = {
            'officer': officer,
        }
        
        return render(request, 'officer_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in officer_dashboard view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while loading the dashboard: {str(e)}")
        return render(request, 'officer_dashboard.html', {'officer': request.user})

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def case_list(request):
    """
    Display a list of all cases with advanced filtering and search capabilities.
    """
    try:
        logger.info("Starting case_list view execution")
        
        # Get base queryset with related data
        logger.info("Fetching base queryset")
        cases = MissingPerson.objects.select_related(
            'reporter'
        ).prefetch_related(
            'updates',
            'officer_updates'
        )
        logger.info(f"Found {cases.count()} total cases")

        # Get filter parameters
        name_filter = request.GET.get('name', '').strip()
        number_filter = request.GET.get('number', '').strip()
        status_filter = request.GET.get('status', '').strip()
        date_filter = request.GET.get('date', '').strip()

        logger.info(f"Applied filters - Name: {name_filter}, Number: {number_filter}, Status: {status_filter}, Date: {date_filter}")

        # Apply name/location filter
        if name_filter:
            cases = cases.filter(
                Q(first_name__icontains=name_filter) |
                Q(last_name__icontains=name_filter) |
                Q(last_seen_location__icontains=name_filter) |
                Q(reporter__first_name__icontains=name_filter) |
                Q(reporter__last_name__icontains=name_filter)
            )
            logger.info(f"After name filter: {cases.count()} cases")

        # Apply case number filter
        if number_filter:
            cases = cases.filter(case_number__icontains=number_filter)
            logger.info(f"After number filter: {cases.count()} cases")

        # Apply status filter
        if status_filter:
            cases = cases.filter(status=status_filter)
            logger.info(f"After status filter: {cases.count()} cases")
        
        # Apply date filter
        if date_filter:
            today = timezone.now().date()
            if date_filter == 'today':
                cases = cases.filter(created_at__date=today)
            elif date_filter == 'week':
                cases = cases.filter(created_at__date__gte=today - timedelta(days=7))
            elif date_filter == 'month':
                cases = cases.filter(created_at__date__gte=today - timedelta(days=30))
            logger.info(f"After date filter: {cases.count()} cases")

        # Calculate statistics
        try:
            total_cases = cases.count()
            stats = {
                'total': total_cases,
                'pending': cases.filter(status='pending').count(),
                'investigation': cases.filter(status='investigation').count(),
                'found': cases.filter(status='found').count(),
                'closed': cases.filter(status='closed').count(),
            }
            logger.info(f"Statistics calculated: {stats}")

            # Calculate percentages
            if total_cases > 0:
                for key in ['pending', 'investigation', 'found', 'closed']:
                    stats[f'{key}_percent'] = round((stats[key] / total_cases) * 100, 1)
        except Exception as stats_error:
            logger.error(f"Error calculating statistics: {str(stats_error)}")
            stats = {
                'total': 0,
                'pending': 0,
                'investigation': 0,
                'found': 0,
                'closed': 0
            }

        # Calculate status counts for filter dropdown
        try:
            status_counts = {
                status: cases.filter(status=status).count()
                for status, _ in MissingPerson.STATUS_CHOICES
            }
            logger.info(f"Status counts calculated: {status_counts}")
        except Exception as count_error:
            logger.error(f"Error calculating status counts: {str(count_error)}")
            status_counts = {}
        
        # Pagination
        try:
            page_number = request.GET.get('page', 1)
            paginator = Paginator(cases.order_by('-created_at'), 10)  # 10 cases per page
            cases = paginator.get_page(page_number)
            logger.info(f"Pagination applied: Page {page_number} of {paginator.num_pages}")
        except Exception as page_error:
            logger.error(f"Error in pagination: {str(page_error)}")
            cases = []
        
        context = {
            'cases': cases,
            'name_filter': name_filter,
            'number_filter': number_filter,
            'status_filter': status_filter,
            'date_filter': date_filter,
            'status_choices': MissingPerson.STATUS_CHOICES,
            'status_counts': status_counts,
            'stats': stats,
            'total_pages': getattr(paginator, 'num_pages', 1),
            'total_cases': total_cases,
            'has_filters': bool(name_filter or number_filter or status_filter or date_filter),
        }
        
        logger.info("Context prepared successfully")
        return render(request, 'officer/officer_view_case.html', context)
        
    except Exception as e:
        logger.error(f"Error in case_list view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while retrieving the cases: {str(e)}")
        return redirect('officer:officer_dashboard')

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def case_detail(request, case_number):
    """Display detailed information about a specific case and handle updates."""
    try:
        case = get_object_or_404(
            MissingPerson.objects.select_related('reporter').prefetch_related('updates', 'officer_updates'),
            case_number=case_number
        )
        
        # Handle form submission
        if request.method == 'POST':
            new_status = request.POST.get('status')
            update_text = request.POST.get('update_text')
            
            # Check if case is already closed
            if case.status == 'closed':
                if new_status != 'closed':
                    messages.error(request, "This case is closed and cannot be reopened.")
                    return redirect('officer:case_detail', case_number=case_number)
                
                # Only allow adding notes to closed cases
                if update_text:
                    case.officer_updates.create(
                        description=update_text,
                        updated_by=request.user
                    )
                    messages.success(request, "Note added to closed case successfully")
                return redirect('officer:case_detail', case_number=case_number)
            
            # Handle status change for non-closed cases
            status_changed = new_status and new_status != case.status
            if status_changed:
                old_status = case.get_status_display()
                case.status = new_status
                
                # Handle found status fields
                if new_status == 'found':
                    found_date = request.POST.get('found_date')
                    location_found = request.POST.get('location_found')
                    
                    if not found_date or not location_found:
                        messages.error(request, "Found date and location are required when marking a case as found.")
                        return redirect('officer:case_detail', case_number=case_number)
                    
                    case.found_date = found_date
                    case.location_found = location_found
                    update_text = f"{update_text}\nPerson found at {location_found} on {found_date}" if update_text else f"Person found at {location_found} on {found_date}"
                
                # Handle closed status fields
                elif new_status == 'closed':
                    closure_date = request.POST.get('closure_date')
                    
                    if not closure_date:
                        messages.error(request, "Closure date is required when closing a case.")
                        return redirect('officer:case_detail', case_number=case_number)
                    
                    case.found_date = closure_date  # Using found_date field for closure date
                    
                    if 'closure_proof_photo' in request.FILES:
                        case.closure_proof_photo = request.FILES['closure_proof_photo']
                        update_text = f"{update_text}\nCase closed on {closure_date} with proof photo" if update_text else f"Case closed on {closure_date} with proof photo"
                    else:
                        update_text = f"{update_text}\nCase closed on {closure_date}" if update_text else f"Case closed on {closure_date}"
                
                case.save()
                
                # Create status change update
                case.officer_updates.create(
                    description=f"Status changed from {old_status} to {case.get_status_display()}. {update_text}",
                    updated_by=request.user
                )
                
                messages.success(request, f"Case status updated to {case.get_status_display()}")
            
            elif update_text:
                # Create general update
                case.officer_updates.create(
                    description=update_text,
                    updated_by=request.user
                )
                messages.success(request, "Case update added successfully")
            
            # Redirect to refresh the page and avoid form resubmission
            return redirect('officer:case_detail', case_number=case_number)
        
        # Get all updates sorted by date
        all_updates = []
        
        # Add case creation
        all_updates.append({
            'date': case.created_at,
            'type': 'creation',
            'description': f'Case reported by {case.reporter.get_full_name()}',
            'by': case.reporter.get_full_name()
        })
        
        # Add case updates
        for update in case.updates.all():
            all_updates.append({
                'date': update.created_at,
                'type': 'update',
                'description': update.description,
                'by': update.created_by.get_full_name() if update.created_by else 'System'
            })
        
        # Add officer updates
        for update in case.officer_updates.all():
            all_updates.append({
                'date': update.updated_at,
                'type': 'officer_update',
                'description': update.description,
                'by': update.updated_by.get_full_name() if update.updated_by else 'System'
            })
        
        # Sort updates by date, newest first
        all_updates.sort(key=lambda x: x['date'], reverse=True)
        
        context = {
            'case': case,
            'updates': all_updates,
            'status_choices': MissingPerson.STATUS_CHOICES
        }
        
        return render(request, 'officer/case_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in case_detail view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while retrieving the case details: {str(e)}")
        return redirect('officer:case_list')

@login_required(login_url='login')
@user_passes_test(is_officer, login_url='login')
def case_update(request, case_number):
    """Update case status and add updates."""
    try:
        case = get_object_or_404(MissingPerson, case_number=case_number)
        
        if request.method == 'POST':
            new_status = request.POST.get('status')
            update_text = request.POST.get('update_text')
            
            if new_status and new_status != case.status:
                old_status = case.get_status_display()
                case.status = new_status
                case.save()
            
                # Create status change update
                case.officer_updates.create(
                    description=f"Status changed from {old_status} to {case.get_status_display()}",
                    updated_by=request.user
                )
                
                messages.success(request, f"Case status updated to {case.get_status_display()}")
            
            if update_text:
                # Create general update
                case.officer_updates.create(
                    description=update_text,
                    updated_by=request.user
                )
                messages.success(request, "Case update added successfully")
            
            return redirect('officer:case_detail', case_number=case_number)
    
        context = {
        'case': case,
            'status_choices': MissingPerson.STATUS_CHOICES
        }
        
        return render(request, 'officer/case_update.html', context)
        
    except Exception as e:
        logger.error(f"Error in case_update view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while updating the case: {str(e)}")
        return redirect('officer:case_list')

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
