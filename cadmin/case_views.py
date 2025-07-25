from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
import logging

from frontend.models import User
from user.models import MissingPerson, CaseUpdate, Feedback

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_admin()

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
        status_counts = MissingPerson.objects.values('status').annotate(count=Count('status'))
        status_choices = MissingPerson.STATUS_CHOICES
        
        # Convert status_counts to a dictionary for easier access in template
        status_count_dict = {item['status']: item['count'] for item in status_counts}

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
            'status_counts': status_count_dict,
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
