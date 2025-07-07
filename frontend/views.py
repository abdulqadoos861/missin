from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from .forms import UserRegistrationForm, ContactForm
from .models import ContactMessage
import logging

logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, 'services.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            send_mail(
                f'Contact Form Submission: {subject}',
                f'You have received a new message from {name} ({email}).\n\nMessage:\n{message}',
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )

            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )

            messages.success(request, 'Thank you for your message! We will get back to you shortly.')
            return redirect('contact')
        else:
            messages.error(request, 'There was an error in your form. Please check the fields and try again.')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {'form': form})

@ensure_csrf_cookie
def login_view(request):
    # Ensure CSRF token is set in cookie
    if request.method == 'GET':
        response = render(request, 'login.html')
        # Set CSRF token in cookie if not present
        if not request.COOKIES.get('csrftoken'):
            response.set_cookie(
                'csrftoken',
                request.META.get('CSRF_COOKIE', ''),
                max_age=60 * 60 * 24 * 7 * 52,  # 1 year
                secure=settings.CSRF_COOKIE_SECURE,
                httponly=False,  # Allow JavaScript to read it
                samesite='Lax'
            )
        return response
        
    if request.method == 'POST':
        # Get CSRF token from cookie and form data for debugging
        csrf_token_cookie = request.COOKIES.get('csrftoken', 'No CSRF token in cookie')
        csrf_token_post = request.POST.get('csrfmiddlewaretoken', 'No CSRF token in POST')
        
        logger.info(f"Login attempt - CSRF Cookie: {csrf_token_cookie}")
        logger.info(f"Login attempt - CSRF POST: {csrf_token_post}")
        
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            if not username or not password:
                messages.error(request, 'Please provide both username and password.')
                response = render(request, 'login.html')
                response.set_cookie('csrftoken', request.META.get('CSRF_COOKIE', ''))
                return response
                
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Your account is not verified. Please check your email for the OTP and verify your account.')
                    response = render(request, 'login.html')
                    response.set_cookie('csrftoken', request.META.get('CSRF_COOKIE', ''))
                    return response
                try:
                    # Log the user in first to establish the session
                    auth_login(request, user)
                    logger.info(f"User {user.username} authenticated successfully")
                    
                    # Create a new session to prevent session fixation
                    request.session.cycle_key()
                    logger.info(f"New session created: {request.session.session_key}")
                    
                    # Set the CSRF token in the response
                    if user.is_admin():
                        logger.info("User is admin, redirecting to admin dashboard")
                        response = redirect('cadmin:admin_dashboard')
                    elif user.is_officer():
                        logger.info("User is officer, redirecting to officer dashboard")
                        response = redirect('officer:officer_dashboard')
                    else:
                        logger.info("User is regular user, redirecting to user dashboard")
                        response = redirect('user_dashboard')
                    
                    # Set CSRF cookie
                    csrf_token = request.META.get('CSRF_COOKIE', '')
                    logger.info(f"Setting CSRF token: {csrf_token}")
                    
                    response.set_cookie(
                        'csrftoken',
                        csrf_token,
                        max_age=60 * 60 * 24 * 7 * 52,  # 1 year
                        secure=settings.CSRF_COOKIE_SECURE if hasattr(settings, 'CSRF_COOKIE_SECURE') else False,
                        httponly=False,
                        samesite='Lax'
                    )
                    
                    messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                    logger.info("Login successful, redirecting...")
                    return response
                    
                except Exception as e:
                    logger.error(f"Error during login process: {str(e)}", exc_info=True)
                    messages.error(request, f'An error occurred during login: {str(e)}')
                    return render(request, 'login.html')
            else:
                messages.error(request, 'Invalid username or password. Please try again.')
                logger.warning(f"Failed login attempt for username: {username}")
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            messages.error(request, f'Login error: {str(e)}. Please try again.')
    
    # If we get here, there was an error or it's a GET request
    response = render(request, 'login.html')
    # Ensure CSRF cookie is set in the response
    response.set_cookie('csrftoken', request.META.get('CSRF_COOKIE', ''), 
                      max_age=60 * 60 * 24 * 7 * 52,  # 1 year
                      domain=settings.SESSION_COOKIE_DOMAIN,
                      secure=settings.CSRF_COOKIE_SECURE,
                      httponly=False,  # Allow JavaScript to read it
                      samesite='Lax')
    return response

@ensure_csrf_cookie
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        try:
            if form.is_valid():
                user = form.save(commit=False)
                # Set user type to regular user by default
                user.user_type = 'user'
                user.is_active = False  # Mark as inactive until OTP verification
                user.save()
                
                # Generate OTP and send it to user's email
                import random
                otp = str(random.randint(100000, 999999))
                request.session['otp'] = otp
                request.session['user_id'] = user.id
                request.session.modified = True
                
                # Send OTP email
                send_mail(
                    'Your OTP for Registration',
                    f'Your One-Time Password (OTP) for registration is: {otp}. Please enter this code to complete your registration.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                
                messages.success(request, 'An OTP has been sent to your email. Please check your inbox to complete registration.')
                return redirect('verify_otp')
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

def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        user_id = request.session.get('user_id')
        
        if entered_otp == stored_otp:
            try:
                from .models import User
                user = User.objects.get(id=user_id)
                # Log the user in
                user.is_active = True  # Activate user after successful verification
                user.save()
                auth_login(request, user)
                # Clear OTP from session
                del request.session['otp']
                del request.session['user_id']
                request.session.modified = True
                
                messages.success(request, 'Registration successful! Welcome to Pakistani Police Force Portal.')
                return redirect('user_dashboard')
            except Exception as e:
                messages.error(request, 'An error occurred during verification. Please try again.')
                print(f"OTP verification error: {str(e)}")
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    
    return render(request, 'otp_verification.html')


@login_required(login_url='login')
def report_incident_redirect(request):
    """
    Redirects authenticated users to the report_missing_person page.
    Unauthenticated users are redirected to the login page first.
    """
    return redirect('report_missing_person')
