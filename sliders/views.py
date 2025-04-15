from rest_framework import viewsets, permissions
from .models import Slider
from .serializers import SliderSerializer

class SliderViewSet(viewsets.ModelViewSet):
    queryset = Slider.objects.all()  # All sliders are shown (no is_active filter needed)
    serializer_class = SliderSerializer
    permission_classes = [permissions.AllowAny]  # Public read access for Flutter app

    def get_permissions(self):
        """Admins can create/update/delete; others only read."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]