from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'chat_type', 'message_preview', 'timestamp', 'is_read')
    list_filter = ('chat_type', 'is_read', 'sender__role', 'receiver__role')
    search_fields = ('sender__username', 'receiver__username', 'message')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    def message_preview(self, obj):
        """Display a truncated version of the message."""
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = 'Message'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser