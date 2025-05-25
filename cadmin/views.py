from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from frontend.models import User
from user.models import MissingPerson, CaseUpdate
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import REDIRECT_FIELD_NAME
import logging

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_admin()

# Create your views here.
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_dashboard(request):
    try:
        # Get case statistics
        cases = MissingPerson.objects.all()
        total_cases = cases.count()
        pending_cases = cases.filter(status='pending').count()
        investigation_cases = cases.filter(status='investigation').count()
        found_cases = cases.filter(status='found').count()
        closed_cases = cases.filter(status='closed').count()

        # Get user statistics
        users = User.objects.all()
        total_users = users.count()
        active_users = users.filter(is_active=True).count()
        inactive_users = users.filter(is_active=False).count()

        context = {
            'total_cases': total_cases,
            'pending_cases': pending_cases,
            'investigation_cases': investigation_cases,
            'found_cases': found_cases,
            'closed_cases': closed_cases,
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
        }
        
        return render(request, 'admin_dashboard.html', context)
    except Exception as e:
        logger.error(f"Error in admin_dashboard view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while loading the dashboard: {str(e)}")
        return render(request, 'admin_dashboard.html', {
            'total_cases': 0,
            'pending_cases': 0,
            'investigation_cases': 0,
            'found_cases': 0,
            'closed_cases': 0,
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
        })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def register_officer(request):
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username')
            email = request.POST.get('email')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone_number = request.POST.get('phone_number')
            address = request.POST.get('address')
            date_of_birth = request.POST.get('date_of_birth')
            cnic = request.POST.get('cnic')
            rank = request.POST.get('rank')
            profile_picture = request.FILES.get('profile_picture')

            # Validate required fields
            if not all([username, email, password1, password2, first_name, last_name, phone_number, address, date_of_birth, cnic, rank]):
                messages.error(request, 'All fields are required.')
                return redirect('register_officer')

            # Validate passwords match
            if password1 != password2:
                messages.error(request, 'Passwords do not match.')
                return redirect('register_officer')

            # Check if username or email already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('register_officer')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('register_officer')

            # Check if CNIC already exists
            if User.objects.filter(cnic=cnic).exists():
                messages.error(request, 'CNIC already registered.')
                return redirect('register_officer')

            # Validate rank
            valid_ranks = ['IGP', 'DIG', 'SSP', 'SP', 'DSP', 'ASP', 'Inspector', 'SI', 'ASI', 'HC', 'Constable']
            if rank not in valid_ranks:
                messages.error(request, 'Invalid rank selected.')
                return redirect('register_officer')

            # Create new officer
            officer = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                address=address,
                date_of_birth=date_of_birth,
                cnic=cnic,
                rank=rank,
                user_type='officer',
                is_active=True  # Set officer as active by default
            )

            # Handle profile picture
            if profile_picture:
                officer.profile_picture = profile_picture
                officer.save()

            messages.success(request, f'Officer {officer.get_full_name()} has been registered successfully.')
            return redirect('manage_users')

        except Exception as e:
            logger.error(f"Error in register_officer view: {str(e)}", exc_info=True)
            messages.error(request, f'An error occurred while registering the officer: {str(e)}')
            return redirect('register_officer')

    return render(request, 'register_officer.html')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def manage_cases(request):
    try:
        # Get all cases with related data
        cases = MissingPerson.objects.select_related(
            'reporter',
            'assigned_officer'
        ).prefetch_related(
            'updates'
        ).all()
        
        # Get search query and filters
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        date_filter = request.GET.get('date', '')
        
        # Apply filters
        if search_query:
            cases = cases.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(case_number__icontains=search_query)
            )
        
        if status_filter:
            cases = cases.filter(status=status_filter)
        
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
        
        return render(request, 'manage_cases.html', context)
        
    except Exception as e:
        logger.error(f"Error in manage_cases view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while retrieving cases: {str(e)}")
        return render(request, 'manage_cases.html', {
            'page_obj': None,
            'total_cases': 0,
            'pending_cases': 0,
            'investigation_cases': 0,
            'found_cases': 0,
            'closed_cases': 0,
        })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_case_details(request, case_id):
    try:
        # Get the case with all related data
        case = get_object_or_404(MissingPerson.objects.select_related(
            'reporter', 
            'assigned_officer'
        ).prefetch_related(
            'updates'
        ), id=case_id)
        
        # Get case updates with related user data
        updates = case.updates.select_related('created_by').all()
        
        # Get available officers for assignment
        available_officers = User.objects.filter(user_type='officer', is_active=True)
        
        context = {
            'case': case,
            'updates': updates,
            'available_officers': available_officers,
        }
        
        return render(request, 'admin_case_details.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_case_details view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while retrieving case details: {str(e)}")
        return redirect('admin_dashboard')

# def manage_user(request):
#     return render(request, 'manage_user.html')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def manage_users(request):
    try:
        # Get all users including officers
        users = User.objects.all().order_by('-date_joined')
        
        # Get search query and filters
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        user_type_filter = request.GET.get('user_type', '')
        date_filter = request.GET.get('date', '')
        
        # Apply filters
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(cnic__icontains=search_query)
            )
        
        if status_filter:
            users = users.filter(is_active=(status_filter == 'active'))
        
        if user_type_filter:
            users = users.filter(user_type=user_type_filter)
        
        if date_filter:
            today = timezone.now()
            if date_filter == 'today':
                users = users.filter(date_joined__date=today.date())
            elif date_filter == 'week':
                week_ago = today - timedelta(days=7)
                users = users.filter(date_joined__gte=week_ago)
            elif date_filter == 'month':
                month_ago = today - timedelta(days=30)
                users = users.filter(date_joined__gte=month_ago)
        
        # Get user statistics from all users (not filtered)
        all_users = User.objects.all()
        total_users = all_users.count()
        active_users = all_users.filter(is_active=True).count()
        inactive_users = all_users.filter(is_active=False).count()
        
        # Get counts by user type from all users
        regular_users = all_users.filter(user_type='user').count()
        officers = all_users.filter(user_type='officer').count()
        admins = all_users.filter(user_type='admin').count()
        
        # Pagination
        paginator = Paginator(users, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'user_type_filter': user_type_filter,
            'date_filter': date_filter,
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'regular_users': regular_users,
            'officers': officers,
            'admins': admins,
        }
        
        return render(request, 'manage_user.html', context)
        
    except Exception as e:
        logger.error(f"Error in manage_users view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while retrieving users: {str(e)}")
        return render(request, 'manage_user.html', {
            'page_obj': None,
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
            'regular_users': 0,
            'officers': 0,
            'admins': 0,
        })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} has been {status}.')
    
    return redirect('manage_users')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def assign_officer(request, case_id):
    if request.method == 'POST':
        try:
            case = get_object_or_404(MissingPerson, id=case_id)
            officer_id = request.POST.get('officer_id')
            
            if officer_id:
                officer = get_object_or_404(User, id=officer_id, user_type='officer')
                case.assigned_officer = officer
                case.save()
                messages.success(request, f'Officer {officer.get_full_name} has been assigned to the case.')
            else:
                case.assigned_officer = None
                case.save()
                messages.success(request, 'Officer assignment has been removed.')
                
        except Exception as e:
            logger.error(f"Error in assign_officer view: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while assigning officer: {str(e)}")
            
    return redirect('admin_case_details', case_id=case_id)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def update_case_status(request, case_id):
    if request.method == 'POST':
        try:
            case = get_object_or_404(MissingPerson, id=case_id)
            new_status = request.POST.get('status')
            
            if new_status in dict(MissingPerson.STATUS_CHOICES):
                case.status = new_status
                case.save()
                messages.success(request, f'Case status has been updated to {case.get_status_display()}.')
            else:
                messages.error(request, 'Invalid status selected.')
                
        except Exception as e:
            logger.error(f"Error in update_case_status view: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while updating status: {str(e)}")
            
    return redirect('admin_case_details', case_id=case_id)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def add_case_update(request, case_id):
    if request.method == 'POST':
        try:
            case = get_object_or_404(MissingPerson, id=case_id)
            description = request.POST.get('description')
            
            if description:
                update = CaseUpdate.objects.create(
                    case=case,
                    description=description,
                    created_by=request.user
                )
                messages.success(request, 'Case update has been added successfully.')
            else:
                messages.error(request, 'Update description cannot be empty.')
                
        except Exception as e:
            logger.error(f"Error in add_case_update view: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while adding update: {str(e)}")
            
    return redirect('admin_case_details', case_id=case_id)
