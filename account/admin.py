from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model with protected fields."""
    list_display = ('username', 'email', 'role', 'is_approved', 'is_active')
    list_filter = ('role', 'is_approved', 'is_active')
    search_fields = ('username', 'email')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Roles', {'fields': ('role', 'is_approved')}),
        ('Permissions', {'fields': ('is_active', 'groups', 'user_permissions')}),
    )
    readonly_fields = ('is_staff', 'is_superuser')  # Protect manual edits
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_approved'),
        }),
    )
    actions = ['approve_vendors']

    def approve_vendors(self, request, queryset):
        """Approve selected vendors."""
        updated = queryset.filter(role='vendor').update(is_approved=True)
        self.message_user(request, f"Approved {updated} vendors.")