# reviews/admin.py
from django.contrib import admin
from .models import Review, ReviewReply
from django.utils.html import format_html

class ReviewReplyInline(admin.TabularInline):
    model = ReviewReply
    extra = 0

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'image_thumbnail', 'created_at')
    list_filter = ('rating', 'product', 'user')
    search_fields = ('user__username', 'product__name', 'product__code', 'product__slug', 'comment')
    inlines = [ReviewReplyInline]

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    image_thumbnail.short_description = 'Image'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(ReviewReply)
class ReviewReplyAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('review__product__name', 'user__username', 'comment')