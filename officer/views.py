from django.shortcuts import render

# Create your views here.
def officer_dashboard(request):
    return render(request, 'officer_dashboard.html')

def view_cases(request):
    return render(request, 'officer_view_case.html')

def update_case(request):
    return render(request, 'officer_update_case.html')

def officer_profile(request):
    return render(request, 'officer_profile.html')
