from django.core.mail import send_mail
from django.http import HttpResponse
from django.views import View
from django.conf import settings

class TestEmailView(View):
    def get(self, request):
        try:
            send_mail(
                'Test Email from Django',
                'This is a test email sent from your Django application.',
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],  # Send to yourself for testing
                fail_silently=False,
            )
            return HttpResponse("Test email sent successfully! Check your inbox.")
        except Exception as e:
            return HttpResponse(f"Failed to send email: {str(e)}", status=500)
