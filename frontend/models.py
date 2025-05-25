from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('user', 'Regular User'),
        ('officer', 'Police Officer'),
        ('admin', 'Admin'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='user')
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fix related name clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='frontend_user_set',
        related_query_name='frontend_user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='frontend_user_set',
        related_query_name='frontend_user'
    )

    def save(self, *args, **kwargs):
        # Set user_type to 'admin' for superusers
        if self.is_superuser:
            self.user_type = 'admin'
        super().save(*args, **kwargs)

    def is_admin(self):
        return self.user_type == 'admin' or self.is_superuser

    def is_officer(self):
        return self.user_type == 'officer'

    def is_regular_user(self):
        return self.user_type == 'user'

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        db_table = 'frontend_user'
