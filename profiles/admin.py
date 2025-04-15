from django.contrib import admin
from .models import Profile, VendorProfile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')
    filter_horizontal = ('wishlist',)

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'user', 'city', 'contact_email')
    search_fields = ('store_name', 'user__username', 'contact_email')