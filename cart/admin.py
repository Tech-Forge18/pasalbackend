# cart/admin.py
from django.contrib import admin
from .models import CartItem

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'quantity', 'selected_color', 'selected_size', 'added_at']
    list_filter = ['user', 'product']
    search_fields = ['user__username', 'product__name', 'product__code', 'product__slug']

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.role == 'vendor'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == 'vendor':
            return qs.filter(product__vendor=request.user)
        return qs