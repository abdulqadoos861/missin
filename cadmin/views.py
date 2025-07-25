from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.db.models import Q
from frontend.models import User
from user.models import MissingPerson, CaseUpdate
from frontend.models import ContactMessage
from .models import MessageReply
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth import REDIRECT_FIELD_NAME
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
import re
import os

logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_admin()

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def reply_to_message(request, message_id):
    message = get_object_or_404(ContactMessage, id=message_id)
    if request.method == 'POST':
        reply_text = request.POST.get('reply_text')
        if reply_text:
            # Save the reply
            MessageReply.objects.create(message=message, reply_text=reply_text)
            
            # Send email
            send_mail(
                f'Re: {message.subject}',
                reply_text,
                settings.DEFAULT_FROM_EMAIL,
                [message.email],
                fail_silently=False,
            )
            
            # Mark message as read
            message.is_read = True
            message.is_replied = True
            message.save()
            
            messages.success(request, 'Your reply has been sent successfully.')
            return redirect('cadmin:view_contact_messages')
        else:
            messages.error(request, 'Reply cannot be empty.')

    return render(request, 'reply_to_message.html', {'message': message})



# Create your views here.
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('index')
    
    try:
        # Get case statistics
        cases = MissingPerson.objects.all()
        total_cases = cases.count()
        pending_cases = cases.filter(status='pending').count()
        investigation_cases = cases.filter(status='investigation').count()
        found_cases = cases.filter(status='found').count()
        closed_cases = cases.filter(status='closed').count()

        # Calculate percentages
        pending_percentage = (pending_cases / total_cases * 100) if total_cases > 0 else 0
        investigation_percentage = (investigation_cases / total_cases * 100) if total_cases > 0 else 0
        found_percentage = (found_cases / total_cases * 100) if total_cases > 0 else 0

        # Get user statistics
        users = User.objects.all()
        total_users = users.count()
        active_users = users.filter(is_active=True).count()
        inactive_users = users.filter(is_active=False).count()

        # Calculate user percentages
        active_percentage = (active_users / total_users * 100) if total_users > 0 else 0
        inactive_percentage = (inactive_users / total_users * 100) if total_users > 0 else 0

        context = {
            'total_cases': total_cases,
            'pending_cases': pending_cases,
            'investigation_cases': investigation_cases,
            'found_cases': found_cases,
            'closed_cases': closed_cases,
            'pending_percentage': pending_percentage,
            'investigation_percentage': investigation_percentage,
            'found_percentage': found_percentage,
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'active_percentage': active_percentage,
            'inactive_percentage': inactive_percentage,
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
            'pending_percentage': 0,
            'investigation_percentage': 0,
            'found_percentage': 0,
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
                return redirect('cadmin:register_officer')

            # Validate passwords match
            if password1 != password2:
                messages.error(request, 'Passwords do not match.')
                return redirect('cadmin:register_officer')

            # Check if username or email already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('cadmin:register_officer')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('cadmin:register_officer')

            # Check if CNIC already exists
            if User.objects.filter(cnic=cnic).exists():
                messages.error(request, 'CNIC already registered.')
                return redirect('cadmin:register_officer')

            # Validate rank
            valid_ranks = ['IGP', 'DIG', 'SSP', 'SP', 'DSP', 'ASP', 'Inspector', 'SI', 'ASI', 'HC', 'Constable']
            if rank not in valid_ranks:
                messages.error(request, 'Invalid rank selected.')
                return redirect('cadmin:register_officer')

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
            return redirect('cadmin:manage_users')

        except Exception as e:
            logger.error(f"Error in register_officer view: {str(e)}", exc_info=True)
            messages.error(request, f'An error occurred while registering the officer: {str(e)}')
            return redirect('cadmin:register_officer')

    officers = User.objects.filter(user_type='officer').order_by('-date_joined')
    context = {
        'officers': officers
    }
    return render(request, 'register_officer.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def edit_officer(request, officer_id):
    officer = get_object_or_404(User, id=officer_id, user_type='officer')
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        cnic = request.POST.get('cnic')
        rank = request.POST.get('rank')
        profile_picture = request.FILES.get('profile_picture')

        # Basic validation
        if not all([first_name, last_name, email, phone_number, address, cnic, rank]):
            messages.error(request, 'All fields except profile picture are required.')
            return render(request, 'edit_officer.html', {'officer': officer})

        # Check for uniqueness of email and CNIC (excluding the current officer)
        if User.objects.filter(email=email).exclude(id=officer_id).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'edit_officer.html', {'officer': officer})

        if User.objects.filter(cnic=cnic).exclude(id=officer_id).exists():
            messages.error(request, 'CNIC already registered.')
            return render(request, 'edit_officer.html', {'officer': officer})

        # Update officer details
        officer.first_name = first_name
        officer.last_name = last_name
        officer.email = email
        officer.phone_number = phone_number
        officer.address = address
        officer.cnic = cnic
        officer.rank = rank

        if profile_picture:
            # Delete old profile picture if it exists
            if officer.profile_picture:
                if default_storage.exists(officer.profile_picture.name):
                    default_storage.delete(officer.profile_picture.name)
            officer.profile_picture = profile_picture

        officer.save()

        messages.success(request, f'Officer {officer.get_full_name()}\'s profile has been updated successfully.')
        return redirect('cadmin:register_officer')

    context = {
        'officer': officer
    }
    return render(request, 'edit_officer.html', context)


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
    
    return redirect('cadmin:manage_users')


@login_required
def admin_settings(request):
    """Admin settings page view"""
    return render(request, 'admin_settings.html')


@login_required
@user_passes_test(is_admin, login_url='login')
def view_contact_messages(request):
    """Display all contact messages in the admin dashboard."""
    messages_list = ContactMessage.objects.all()
    paginator = Paginator(messages_list, 15)  # Show 15 messages per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Mark messages as read when they are viewed
    for msg in page_obj:
        if not msg.is_read:
            msg.is_read = True
            msg.save(update_fields=['is_read'])

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'contact_messages.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def update_admin_profile(request):
    """Update admin profile information"""
    if request.method == 'POST':
        try:
            user = request.user
            
            # Get and validate form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            address = request.POST.get('address', '').strip()
            cnic = request.POST.get('cnic', '').strip()
            date_of_birth = request.POST.get('date_of_birth')
            
            # Validate required fields
            if not all([first_name, last_name, email, phone_number, address, cnic, date_of_birth]):
                messages.error(request, 'All fields are required.')
                return redirect('cadmin:admin_settings')
            
            # Validate email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                messages.error(request, 'Please enter a valid email address.')
                return redirect('cadmin:admin_settings')
            
            # Validate CNIC format
            if not re.match(r'^\d{5}-\d{7}-\d{1}$', cnic):
                messages.error(request, 'Please enter a valid CNIC number (e.g., 33201-0649966-2).')
                return redirect('cadmin:admin_settings')
            
            # Check if email is already taken by another user
            if User.objects.exclude(id=user.id).filter(email=email).exists():
                messages.error(request, 'This email is already registered to another user.')
                return redirect('cadmin:admin_settings')
            
            # Check if CNIC is already taken by another user
            if User.objects.exclude(id=user.id).filter(cnic=cnic).exists():
                messages.error(request, 'This CNIC is already registered to another user.')
                return redirect('cadmin:admin_settings')
            
            # Update user information
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone_number = phone_number
            user.address = address
            user.cnic = cnic
            
            # Convert date string to date object
            try:
                user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format.')
                return redirect('cadmin:admin_settings')
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                # Delete old profile picture if exists
                if user.profile_picture:
                    try:
                        os.remove(user.profile_picture.path)
                    except:
                        pass
                user.profile_picture = request.FILES['profile_picture']
            
            # Save changes
            try:
                # For superuser, we need to save all fields
                if user.is_superuser:
                    user.save()
                else:
                    user.save(update_fields=[
                        'first_name', 'last_name', 'email', 'phone_number',
                        'address', 'cnic', 'date_of_birth', 'profile_picture'
                    ])
                
                # Update session to reflect changes
                update_session_auth_hash(request, user)
                
                messages.success(request, 'Profile updated successfully!')
                logger.info(f"Admin profile updated successfully for user: {user.username}")
            except Exception as save_error:
                messages.error(request, f'Error saving profile: {str(save_error)}')
                logger.error(f"Error saving admin profile: {str(save_error)}", exc_info=True)
                return redirect('cadmin:admin_settings')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            logger.error(f"Error updating admin profile: {str(e)}", exc_info=True)
    
    return redirect('cadmin:admin_settings')

@login_required
def change_admin_password(request):
    """Change admin password"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect!')
            return redirect('admin_settings')
        
        # Validate new password
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match!')
            return redirect('admin_settings')
        
        # Validate password strength
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return redirect('admin_settings')
        
        try:
            # Update password
            request.user.set_password(new_password)
            request.user.save()
            
            # Update session to prevent logout
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Password changed successfully!')
            
        except Exception as e:
            messages.error(request, f'Error changing password: {str(e)}')
    
    return redirect('admin_settings')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_feedback(request):
    """Display all user feedback in the admin dashboard."""
    from user.models import Feedback
    feedbacks = Feedback.objects.all().order_by('-created_at')
    paginator = Paginator(feedbacks, 15)  # Show 15 feedbacks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'feedbacks': page_obj,
    }
    return render(request, 'admin_feedback.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def reply_feedback(request, feedback_id):
    """Handle reply to user feedback."""
    from user.models import Feedback
    from django.utils import timezone
    feedback = get_object_or_404(Feedback, id=feedback_id)
    
    if request.method == 'POST':
        reply_text = request.POST.get('reply_text')
        if reply_text:
            feedback.reply = reply_text
            feedback.reply_date = timezone.now()
            feedback.is_resolved = True
            feedback.save()
            
            # Optionally send an email to the user
            if feedback.user.email:
                try:
                    send_mail(
                        f'Re: Feedback - {feedback.title}',
                        reply_text,
                        settings.DEFAULT_FROM_EMAIL,
                        [feedback.user.email],
                        fail_silently=False,
                    )
                    messages.success(request, 'Your reply has been sent successfully.')
                except Exception as e:
                    logger.error(f"Error sending email: {str(e)}")
                    messages.warning(request, 'Reply saved, but failed to send email notification.')
            else:
                messages.success(request, 'Your reply has been saved.')
            return redirect('cadmin:admin_feedback')
        else:
            messages.error(request, 'Reply cannot be empty.')
    
    return redirect('cadmin:admin_feedback')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_officer(request, officer_id):
    officer = get_object_or_404(User, id=officer_id, user_type='officer')
    if request.method == 'POST':
        officer.delete()
        messages.success(request, 'Officer deleted successfully.')
        return redirect('cadmin:register_officer')
    return render(request, 'register_officer.html', {'officer': officer})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('cadmin:manage_users')
    return render(request, 'manage_user.html', {'user': user})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_message(request, message_id):
    message = get_object_or_404(ContactMessage, id=message_id)
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Message deleted successfully.')
        return redirect('cadmin:view_contact_messages')
    return render(request, 'contact_messages.html', {'message': message})

def activity_logs(request):
    """
    View to display system activity logs.
    This is a placeholder that needs to be implemented with actual activity log data.
    """
    # TODO: Implement actual activity log retrieval logic
    context = {
        'page_title': 'Activity Logs',
        'activities': [],  # Replace with actual activity log data
    }
    return render(request, 'activity_logs.html', context)


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def case_list(request):
    """
    Display a list of all cases with advanced filtering and search capabilities.
    """
    try:
        # Get base queryset with related data
        cases = MissingPerson.objects.select_related(
            'reporter'
        ).prefetch_related(
            'updates'
        ).all()

        # Get filter parameters
        name_filter = request.GET.get('name', '').strip()
        number_filter = request.GET.get('number', '').strip()
        status_filter = request.GET.get('status', '').strip()
        date_filter = request.GET.get('date', '').strip()

        # Apply name/location filter
        if name_filter:
            cases = cases.filter(
                Q(first_name__icontains=name_filter) |
                Q(last_name__icontains=name_filter) |
                Q(last_seen_location__icontains=name_filter) |
                Q(reporter__first_name__icontains=name_filter) |
                Q(reporter__last_name__icontains=name_filter)
            )

        # Apply case number filter
        if number_filter:
            cases = cases.filter(case_number__icontains=number_filter)

        # Apply status filter
        if status_filter:
            cases = cases.filter(status=status_filter)
        
        # Apply date filter
        if date_filter:
            today = timezone.now().date()
            if date_filter == 'today':
                cases = cases.filter(created_at__date=today)
            elif date_filter == 'week':
                cases = cases.filter(created_at__date__gte=today - timedelta(days=7))
            elif date_filter == 'month':
                cases = cases.filter(created_at__date__gte=today - timedelta(days=30))

        # Order by most recent first
        cases = cases.order_by('-created_at')

        # Get case statistics for filters
        status_choices = MissingPerson.STATUS_CHOICES
        
        # Get counts for each status
        status_count_dict = {}
        for status, _ in status_choices:
            status_count_dict[status] = MissingPerson.objects.filter(status=status).count()

        # Pagination
        paginator = Paginator(cases, 15)  # 15 cases per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'cases': page_obj.object_list,  # Pass the paginated cases
            'name_filter': name_filter,
            'number_filter': number_filter,
            'status_filter': status_filter,
            'date_filter': date_filter,
            'status_choices': status_choices,
            'status_count_dict': status_count_dict,  # Changed from status_counts to status_count_dict
            'total_cases': paginator.count,
        }

        return render(request, 'cadmin/case_list.html', context)

    except Exception as e:
        logger.error(f"Error in case_list view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while loading cases: {str(e)}")
        return render(request, 'cadmin/case_list.html', {'cases': []})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def case_detail(request, case_id):
    """
    Display detailed information about a specific case and handle updates.
    """
    try:
        # Get the case with related data
        case = get_object_or_404(
            MissingPerson.objects.select_related('reporter').prefetch_related('updates'),
            id=case_id
        )
        
        # Get all updates for this case
        updates = case.updates.all().order_by('-created_at')
        
        # Get all available status choices from the model
        status_choices = MissingPerson.STATUS_CHOICES
        
        context = {
            'case': case,
            'updates': updates,
            'status_choices': status_choices,
        }
        
        return render(request, 'cadmin/case_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in case_detail view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while loading the case details: {str(e)}")
        return redirect('cadmin:manage_cases')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def case_update(request, case_id):
    """
    Update case status and add updates.
    """
    if request.method == 'POST':
        try:
            case = get_object_or_404(MissingPerson, id=case_id)
            status = request.POST.get('status')
            description = request.POST.get('description', '').strip()
            
            # Update case status if changed
            if status and status != case.status:
                case.status = status
                case.save()
                
                # Add automatic update for status change
                if description:
                    description = f"Status changed to {case.get_status_display()}. {description}"
                else:
                    description = f"Status changed to {case.get_status_display()}."
                
                messages.success(request, f"Case status updated to {case.get_status_display()}.")
            
            # Add update if description is provided
            if description:
                CaseUpdate.objects.create(
                    case=case,
                    description=description,
                    created_by=request.user
                )
                messages.success(request, "Case update added successfully.")
            
            return redirect('cadmin:admin_case_details', case_id=case.id)
            
        except Exception as e:
            logger.error(f"Error in case_update view: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while updating the case: {str(e)}")
    
    return redirect('cadmin:admin_case_details', case_id=case_id)

