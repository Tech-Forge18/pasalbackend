from django.contrib import admin
from .models import Slider

@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ('image',)  # Show only the image in the list
    fields = ('image',)  # Only image field in the add/edit form

    def get_queryset(self, request):
        """Only admins can manage sliders."""
        qs = super().get_queryset(request)
        if request.user.role != 'admin':
            return qs.none()  # Vendors/customers can’t see sliders in admin
        return qs