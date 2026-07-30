from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Extra profile fields for a customer, linked 1:1 to Django's built-in User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    is_blocked = models.BooleanField(default=False, help_text="Admin can block a user without deleting their account.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.username}"
