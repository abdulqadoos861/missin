from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Case, CaseUpdate
from user.models import MissingPerson

# Create your views here.
@login_required
def officer_dashboard(request):
    # Get case statistics
    total_cases = MissingPerson.objects.filter(assigned_officer=request.user).count()
    solved_cases = MissingPerson.objects.filter(assigned_officer=request.user, status='found').count()
    pending_cases = MissingPerson.objects.filter(assigned_officer=request.user, status='pending').count()
    recent_cases = MissingPerson.objects.filter(assigned_officer=request.user).order_by('-created_at')[:5]
    
    context = {
        'total_cases': total_cases,
        'solved_cases': solved_cases,
        'pending_cases': pending_cases,
        'recent_cases': recent_cases,
    }
    return render(request, 'officer_dashboard.html', context)

@login_required
def view_cases(request):
    cases = MissingPerson.objects.filter(assigned_officer=request.user).order_by('-created_at')
    return render(request, 'officer_view_case.html', {'cases': cases})

@login_required
def view_case_detail(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id, assigned_officer=request.user)
    updates = case.officer_updates.all().order_by('-created_at')
    return render(request, 'officer_view_case_detail.html', {
        'case': case,
        'updates': updates
    })

@login_required
def update_case(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id, assigned_officer=request.user)
    
    if request.method == 'POST':
        try:
            # Get the new status
            new_status = request.POST.get('status')
            
            # Check if evidence is required (when closing the case)
            if new_status == 'closed' and not request.FILES.get('evidence_document'):
                messages.error(request, 'Evidence document is required when closing a case.')
                return render(request, 'officer_update_case.html', {'case': case})
            
            # Update case fields
            case.status = new_status
            case.priority = request.POST.get('priority')
            case.notes = request.POST.get('notes')
            
            # Handle evidence document if provided
            if request.FILES.get('evidence_document'):
                case.evidence_document = request.FILES['evidence_document']
            
            case.save()
            
            # Create case update
            if request.POST.get('update_description'):
                CaseUpdate.objects.create(
                    case=case,
                    description=request.POST.get('update_description'),
                    updated_by=request.user
                )
            
            messages.success(request, 'Case updated successfully.')
            return redirect('officer_view_case_detail', case_id=case.id)
            
        except Exception as e:
            messages.error(request, f'Error updating case: {str(e)}')
    
    return render(request, 'officer_update_case.html', {'case': case})

@login_required
def officer_profile(request):
    if request.method == 'POST':
        try:
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
            
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
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
