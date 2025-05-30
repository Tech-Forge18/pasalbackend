from rest_framework import serializers
from .models import Slider

class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = ['image']  # Only serialize the image field
        