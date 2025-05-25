from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
from .forms import UserRegistrationForm
import logging

logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    return render(request, 'index.html')

@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                auth_login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Debug logging
                logger.info(f"User {user.username} logged in")
                logger.info(f"User type: {user.user_type}")
                logger.info(f"Is admin: {user.is_admin()}")
                
                # Redirect based on user type
                if user.is_admin():
                    logger.info("Redirecting to admin dashboard")
                    return redirect('admin_dashboard')
                elif user.is_officer():
                    logger.info("Redirecting to officer dashboard")
                    return redirect('officer_dashboard')
                else:  # regular user
                    logger.info("Redirecting to user dashboard")
                    return redirect('user_dashboard')
            else:
                messages.error(request, 'Invalid username or password. Please try again.')
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred during login. Please try again.')
    
    return render(request, 'login.html')

@ensure_csrf_cookie
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        try:
            if form.is_valid():
                user = form.save(commit=False)
                # Set user type to regular user by default
                user.user_type = 'user'
                user.save()
                
                # Log the user in
                auth_login(request, user)
                
                messages.success(request, 'Registration successful! Welcome to Pakistani Police Force Portal.')
                return redirect('user_dashboard')
            else:
                # Form validation failed
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'An error occurred during registration. Please try again.')
            # Log the error for debugging
            print(f"Registration error: {str(e)}")
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})

