from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'display_name', 'created_at', 'updated_at']
    search_fields = ['user__username', 'display_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
