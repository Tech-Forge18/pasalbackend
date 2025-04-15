from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Basic serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'is_approved']
        read_only_fields = ['id', 'username']