# products/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Product, Category, Promotion, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'get_vendor', 'price', 'stock', 'is_exclusive_deal', 'is_trending', 'created_at', 'vendor_dashboard_link')
    list_filter = ('is_exclusive_deal', 'is_trending', 'category')
    search_fields = ('name', 'description', 'code', 'slug', 'brand')
    list_editable = ('is_exclusive_deal', 'is_trending')
    fields = (
        'name', 'description', 'brand', 'specification', 'price', 'original_price', 'discount',
        'image', 'category', 'color', 'sizes', 'is_exclusive_deal', 'deal_end_time',
        'is_trending', 'vendor', 'stock', 'stock_threshold', 'code', 'slug', 'rating', 'sold_count'
    )
    readonly_fields = ('created_at', 'rating', 'sold_count', 'slug')
    inlines = [ProductImageInline]

    def get_vendor(self, obj):
        return obj.vendor.username if obj.vendor else 'None'
    get_vendor.short_description = 'Vendor'

    def vendor_dashboard_link(self, obj):
        if obj.vendor and obj.vendor == self.request.user and self.request.user.role == 'vendor':
            url = reverse('api:product-vendor-dashboard')
            return format_html('<a href="{}">View Dashboard</a>', url)
        return 'N/A'
    vendor_dashboard_link.short_description = 'Dashboard'

    def get_queryset(self, request):
        self.request = request
        qs = super().get_queryset(request)
        if request.user.role == 'vendor' and not request.user.is_approved:
            return qs.none()
        elif request.user.role == 'vendor':
            return qs.filter(vendor=request.user)
        return qs

    def save_model(self, request, obj, form, change):
        if not change and not obj.vendor and request.user.role == 'vendor':
            obj.vendor = request.user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.role == 'vendor':
            if 'vendor' in form.base_fields:
                form.base_fields['vendor'].disabled = True
                form.base_fields['vendor'].initial = request.user
            if 'category' in form.base_fields:
                form.base_fields['category'].queryset = Category.objects.filter(vendor=request.user)
        return form

    def has_change_permission(self, request, obj=None):
        if request.user.role == 'vendor' and not request.user.is_approved:
            return False
        elif request.user.role == 'vendor':
            return obj is None or obj.vendor == request.user
        return True

    def has_delete_permission(self, request, obj=None):
        if request.user.role == 'vendor' and not request.user.is_approved:
            return False
        elif request.user.role == 'vendor':
            return obj is not None and obj.vendor == request.user
        return True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_vendor', 'parent_category_name', 'subcategories_list', 'image')
    search_fields = ('name',)
    list_filter = ('parent_category',)

    def get_vendor(self, obj):
        return obj.vendor.username if obj.vendor else 'None'
    get_vendor.short_description = 'Vendor'

    def parent_category_name(self, obj):
        return obj.parent_category.name if obj.parent_category else 'None'
    parent_category_name.short_description = 'Parent Category'

    def subcategories_list(self, obj):
        return ", ".join([sub.name for sub in obj.subcategories.all()])
    subcategories_list.short_description = 'Subcategories'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == 'vendor' and not request.user.is_approved:
            return qs.none()
        elif request.user.role == 'vendor':
            return qs.filter(vendor=request.user)
        return qs

    def save_model(self, request, obj, form, change):
        if not change and not obj.vendor and request.user.role == 'vendor':
            obj.vendor = request.user
        super().save_model(request, obj, form, change)

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'vendor', 'start_date', 'end_date', 'is_active')
    list_filter = ('vendor', 'start_date', 'end_date')
    search_fields = ('code',)

    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == 'vendor' and not request.user.is_approved:
            return qs.none()
        elif request.user.role == 'vendor':
            return qs.filter(vendor=request.user)
        return qs

    def save_model(self, request, obj, form, change):
        if not change and not obj.vendor and request.user.role == 'vendor':
            obj.vendor = request.user
        super().save_model(request, obj, form, change)

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'created_at')
    search_fields = ('product__name',)
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == 'vendor' and not request.user.is_approved:
            return qs.none()
        elif request.user.role == 'vendor':
            return qs.filter(product__vendor=request.user)
        return qs