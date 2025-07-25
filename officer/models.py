from django.db import models
from django.conf import settings
from frontend.models import User
from user.models import MissingPerson

class CaseUpdate(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('under_investigation', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PROGRESS_CHOICES = [
        ('0', '0%'),
        ('25', '25%'),
        ('50', '50%'),
        ('75', '75%'),
        ('100', '100%'),
    ]

    case = models.ForeignKey(MissingPerson, on_delete=models.CASCADE, related_name='officer_updates')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    progress = models.CharField(max_length=3, choices=PROGRESS_CHOICES, default='0')
    description = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='officer_case_updates')

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Update for {self.case.case_number} - {self.updated_at.strftime('%Y-%m-%d')}"

class CaseNote(models.Model):
    case = models.ForeignKey(MissingPerson, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
 
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note: {self.title} - {self.created_at.strftime('%Y-%m-%d')}"

class CaseEvidence(models.Model):
    EVIDENCE_TYPES = [
        ('photo', 'Photograph'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]

    case = models.ForeignKey(MissingPerson, on_delete=models.CASCADE, related_name='evidence')
    title = models.CharField(max_length=200, default='Missing Person Evidence')
    description = models.TextField(default='Evidence related to missing person case')
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default='photo')
    file = models.FileField(upload_to='missing_person_evidence/')
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Missing Person Evidence'
        verbose_name_plural = 'Missing Person Evidence'

    def __str__(self):
        return f"Evidence: {self.get_evidence_type_display()} - {self.created_at.strftime('%Y-%m-%d')}"
