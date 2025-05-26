from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Case, CaseUpdate, CaseNote, CaseEvidence
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
    updates = case.officer_updates.all().order_by('-updated_at')
    return render(request, 'officer_view_case_detail.html', {
        'case': case,
        'updates': updates
    })

@login_required
def update_case(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id, assigned_officer=request.user)
    
    if request.method == 'POST':
        try:
            status = request.POST.get('status')
            progress = request.POST.get('progress')
            description = request.POST.get('description')
            
            if not all([status, progress, description]):
                messages.error(request, 'All fields are required.')
                return redirect('officer_view_case_detail', case_id=case.id)
            
            CaseUpdate.objects.create(
                case=case,
                status=status,
                progress=progress,
                description=description,
                updated_by=request.user
            )
            
            messages.success(request, 'Case updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating case: {str(e)}')
    
    return redirect('officer_view_case_detail', case_id=case.id)

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

@login_required
def add_case_note(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id, assigned_officer=request.user)
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            content = request.POST.get('content')
            
            if not title or not content:
                messages.error(request, 'Title and content are required.')
                return redirect('officer_view_case_detail', case_id=case.id)
            
            CaseNote.objects.create(
                case=case,
                title=title,
                content=content,
                created_by=request.user
            )
            
            messages.success(request, 'Note added successfully.')
        except Exception as e:
            messages.error(request, f'Error adding note: {str(e)}')
    
    return redirect('officer_view_case_detail', case_id=case.id)

@login_required
def add_case_evidence(request, case_id):
    case = get_object_or_404(MissingPerson, id=case_id, assigned_officer=request.user)
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description')
            file = request.FILES.get('file')
            
            if not title or not description or not file:
                messages.error(request, 'All fields are required.')
                return redirect('officer_view_case_detail', case_id=case.id)
            
            CaseEvidence.objects.create(
                case=case,
                title=title,
                description=description,
                file=file,
                uploaded_by=request.user
            )
            
            messages.success(request, 'Evidence added successfully.')
        except Exception as e:
            messages.error(request, f'Error adding evidence: {str(e)}')
    
    return redirect('officer_view_case_detail', case_id=case.id)
