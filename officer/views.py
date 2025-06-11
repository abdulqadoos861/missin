import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages, auth
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth import logout as auth_logout
from django.template import RequestContext
from .models import Case, CaseUpdate, CaseNote, CaseEvidence
from user.models import MissingPerson
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Create your views here.
@login_required
def officer_dashboard(request):
    # Get case statistics (exclude closed cases for active counts)
    all_cases = MissingPerson.objects.all()
    total_cases = all_cases.exclude(status='closed').count()
    solved_cases = all_cases.filter(status='found').count()
    pending_cases = all_cases.filter(status='pending').count()
    cases_closed = all_cases.filter(status='closed').count()
    
    # Calculate success rate (avoid division by zero)
    success_rate = 0
    if total_cases > 0:
        success_rate = round((solved_cases / total_cases) * 100)
    
    context = {
        'total_cases': total_cases,
        'solved_cases': solved_cases,
        'pending_cases': pending_cases,
        'cases_closed': cases_closed,
        'success_rate': success_rate,
        'current_date': timezone.now(),
    }
    return render(request, 'officer_dashboard.html', context)

@login_required
def view_cases(request):
    # Get all non-closed cases by default
    cases_list = MissingPerson.objects.exclude(status='closed').order_by('-created_at')
    
    # Apply search filter
    search_query = request.GET.get('search', '')
    if search_query:
        cases_list = cases_list.filter(
            Q(name__icontains=search_query) |
            Q(contact_phone__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Apply status filter
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter.lower() == 'closed':
            # Only show closed cases if explicitly filtered
            cases_list = MissingPerson.objects.filter(status='closed').order_by('-created_at')
        elif status_filter.lower() != 'all':
            # Filter by specific status
            cases_list = cases_list.filter(status=status_filter)
    
    # Apply date filter
    date_filter = request.GET.get('date')
    if date_filter:
        cases_list = cases_list.filter(created_at__date=date_filter)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(cases_list, 10)  # Show 10 cases per page
    
    try:
        cases = paginator.page(page)
    except PageNotAnInteger:
        cases = paginator.page(1)
    except EmptyPage:
        cases = paginator.page(paginator.num_pages)
    
    # Get counts for each status
    status_counts = {
        'pending_count': MissingPerson.objects.filter(status='pending').count(),
        'investigation_count': MissingPerson.objects.filter(status='investigation').count(),
        'found_count': MissingPerson.objects.filter(status='found').count(),
        'closed_count': MissingPerson.objects.filter(status='closed').count(),
    }
    
    context = {
        'cases': cases,
        **status_counts,
        'search_query': search_query,
    }
    
    return render(request, 'officer_view_case.html', context)

@login_required
def officer_view_case_detail(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id)
    updates = CaseUpdate.objects.filter(case=case).order_by('-updated_at')
    evidence_photos = CaseEvidence.objects.filter(case=case, evidence_type='photo')

    context = {
        'case': case,
        'updates': updates,
        'evidence_photos': evidence_photos,
    }
    return render(request, 'officer_view_case_detail.html', context)

@login_required
def add_case_update(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id)
    if request.method == 'POST':
        description = request.POST.get('description')
        if description:
            CaseUpdate.objects.create(
                case=case, 
                updated_by=request.user, 
                description=description
            )
            messages.success(request, 'Case update added successfully.')
        else:
            messages.error(request, 'Update description cannot be empty.')
    return redirect('officer:officer_view_case_detail', case_id=case.id)

@login_required
def update_case_status(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        case.status = status

        update_description = f'Case status updated to {status}.'

        if status == 'closed':
            closure_photo = request.FILES.get('closure_proof_photo')
            if not closure_photo:
                messages.error(request, 'A closure proof photo is required to close the case.')
                return redirect('officer:officer_view_case_detail', case_id=case.id)
            case.closure_proof_photo = closure_photo

        if status == 'found':
            date_found = request.POST.get('date_found')
            location_found = request.POST.get('location_found')
            closing_remarks = request.POST.get('closing_remarks')

            case.date_found = date_found
            case.location_found = location_found
            case.closing_remarks = closing_remarks
            
            update_description += f" Found on {date_found} at {location_found}. Remarks: {closing_remarks}"

        CaseUpdate.objects.create(
            case=case, 
            updated_by=request.user, 
            description=update_description
        )
        case.save()
        messages.success(request, 'Case status updated successfully.')
    return redirect('officer:officer_view_case_detail', case_id=case.id)

@login_required
def update_case(request, case_id):
    try:
        case = MissingPerson.objects.get(id=case_id)
        
        # Check if case is already closed
        if case.status == 'closed':
            return JsonResponse({
                'success': False,
                'message': 'This case is closed and cannot be modified.'
            })
        
        if request.method == 'POST':
            status = request.POST.get('status')
            note = request.POST.get('note')
            
            # Validate inputs
            if not status or not note:
                return JsonResponse({
                    'success': False,
                    'message': 'Both status and note are required.'
                })
            
            # Validate status value
            valid_statuses = ['pending', 'under_progress', 'found', 'closed']
            if status.lower() not in valid_statuses:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid status value.'
                })
            
            # Check if status is being changed to 'closed'
            if status.lower() == 'closed' and case.status.lower() != 'closed':
                # Increment cases_closed counter for the officer
                if case.assigned_officer:
                    case.assigned_officer.cases_closed += 1
                    case.assigned_officer.save()
            
            # Update case status
            case.status = status
            case.save()
            
            # Create case update
            CaseUpdate.objects.create(
                case=case,
                status=status,
                description=note,
                updated_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Case status updated successfully.',
                'redirect_url': reverse('officer:officer_view_case_detail', args=[case.id])
            })
            
    except MissingPerson.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Case not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@login_required
def officer_profile(request):
    try:
        if request.method == 'POST':
            # Update user information
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            
            # Handle password change
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            
            if current_password and new_password:
                if user.check_password(current_password):
                    user.set_password(new_password)
                else:
                    messages.error(request, 'Current password is incorrect.')
                    return redirect('officer_profile')
            
            # Handle profile picture
            if request.FILES.get('profile_picture'):
                user.profile_picture = request.FILES['profile_picture']
            
            # Save user changes
            user.save()
            
            # Update notification settings
            user.notification_settings = {
                'email_notifications': request.POST.get('email_notifications') == 'on',
                'case_updates': request.POST.get('case_updates') == 'on',
                'system_notifications': request.POST.get('system_notifications') == 'on'
            }
            user.save()
            
            messages.success(request, 'Settings updated successfully.')
            return redirect('officer_profile')
        
        # Get case statistics
        total_cases = MissingPerson.objects.filter(assigned_officer=request.user).count()
        solved_cases = MissingPerson.objects.filter(assigned_officer=request.user, status='found').count()
        pending_cases = MissingPerson.objects.filter(assigned_officer=request.user, status='pending').count()
        
        context = {
            'total_cases': total_cases,
            'solved_cases': solved_cases,
            'pending_cases': pending_cases,
        }
        return render(request, 'officer_profile.html', context)
    except Exception as e:
        messages.error(request, f'Error updating profile: {str(e)}')
        return redirect('officer_profile')

@login_required
def add_case_note(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id, assigned_officer=request.user)
    
    # Check if case is closed
    if case.status == 'closed':
        messages.error(request, 'Cannot add note: This case is closed.')
        return redirect('officer:officer_view_case_detail', case_id=case.id)
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            content = request.POST.get('content')
            
            if not title or not content:
                messages.error(request, 'Title and content are required.')
                return redirect('officer:officer_view_case_detail', case_id=case.id)
            
            CaseNote.objects.create(
                case=case,
                title=title,
                content=content,
                created_by=request.user
            )
            
            messages.success(request, 'Note added successfully.')
        except Exception as e:
            messages.error(request, f'Error adding note: {str(e)}')
    
    return redirect('officer:officer_view_case_detail', case_id=case.id)

@login_required
def add_case_evidence(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id, assigned_officer=request.user)
    
    # Check if case is closed
    if case.status == 'closed':
        messages.error(request, 'Cannot add evidence: This case is closed.')
        return redirect('officer:officer_view_case_detail', case_id=case.id)
    
    if request.method == 'POST':
        evidence_file = request.FILES.get('evidence_file')
        description = request.POST.get('description', '')
        
        if not evidence_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('officer:officer_view_case_detail', case_id=case.id)
        
        try:
            # Create a new evidence record
            evidence = CaseEvidence(
                case=case,
                uploaded_by=request.user,
                file=evidence_file,
                description=description,
                title=os.path.splitext(evidence_file.name)[0]  # Use filename as title
            )
            evidence.save()
            
            # Add an update about the new evidence
            update = CaseUpdate(
                case=case,
                updated_by=request.user,
                update_type='evidence_added',
                description=f'New evidence added: {description or "No description provided"}'
            )
            update.save()
            
            messages.success(request, 'Evidence added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding evidence: {str(e)}')
    
    return redirect('officer:officer_view_case_detail', case_id=case.id)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def officer_logout(request):
    """Custom logout view for officers"""
    auth_logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')