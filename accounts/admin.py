from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'is_blocked', 'created_at')
    list_filter = ('is_blocked', 'city')
    search_fields = ('user__username', 'user__email', 'phone')
