from django.db import models
from frontend.models import User

# Create your models here.

class CaseUpdate(models.Model):
    case = models.ForeignKey('MissingPerson', on_delete=models.CASCADE, related_name='updates')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='user_case_updates')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update for {self.case.case_number} - {self.created_at.strftime('%Y-%m-%d')}"

class MissingPerson(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('investigation', 'Under Investigation'),
        ('found', 'Found'),
        ('closed', 'Closed'),
    )

    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    height = models.CharField(max_length=50, help_text="Height in feet and inches")
    weight = models.CharField(max_length=50, help_text="Weight in kg", blank=True)
    
    # Physical Description
    eye_color = models.CharField(max_length=50)
    hair_color = models.CharField(max_length=50)
    skin_color = models.CharField(max_length=50, blank=True)
    distinguishing_marks = models.TextField(blank=True, help_text="Scars, tattoos, or other identifying marks")
    
    # Last Seen Information
    last_seen_date = models.DateField()
    last_seen_location = models.CharField(max_length=255)
    last_seen_wearing = models.TextField(help_text="Description of clothes last seen wearing")
    
    # Contact Information
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_missing_persons')
    contact_number = models.CharField(max_length=15)
    additional_contact = models.CharField(max_length=15, blank=True)
    
    # Case Details
    case_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='assigned_missing_persons')
    
    # Found Information
    location_found = models.CharField(max_length=255, blank=True, null=True)
    found_date = models.DateField(blank=True, null=True)
    
    # Additional Information
    description = models.TextField(help_text="Additional details about the missing person")
    photo = models.ImageField(upload_to='missing_persons/')
    additional_photo_1 = models.ImageField(upload_to='missing_persons/additional/', blank=True, null=True)
    additional_photo_2 = models.ImageField(upload_to='missing_persons/additional/', blank=True, null=True)
    additional_photo_3 = models.ImageField(upload_to='missing_persons/additional/', blank=True, null=True)
    closure_proof_photo = models.ImageField(upload_to='missing_persons/closure_proofs/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.case_number}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_status_display(self, status=None):
        if status is None:
            status = self.status
        return dict(self.STATUS_CHOICES).get(status, status)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Missing Person'
        verbose_name_plural = 'Missing Persons'

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback')
    feedback_type = models.CharField(max_length=50, blank=True, help_text="Type of feedback")
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.IntegerField(default=0, help_text="Rating out of 5")
    reply = models.TextField(blank=True, null=True, help_text="Reply from the admin or officer")
    reply_date = models.DateTimeField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback from {self.user.username} - {self.title}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
