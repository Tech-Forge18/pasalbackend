# account/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.validators import validate_email
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Basic serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_approved', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'is_approved']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords must match"})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists"})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists"})
        role = data.get('role', 'customer')
        if role not in ['customer', 'vendor', 'admin']:
            raise serializers.ValidationError({"role": "Invalid role"})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user or not user.is_active:
            raise serializers.ValidationError("Invalid credentials")
        if user.role == 'vendor' and not user.is_approved:
            raise serializers.ValidationError("Vendor account not approved by admin")
        return user

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        validate_email(value)
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    token = serializers.CharField()

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords must match"})
        return data

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            RefreshToken(value)
        except Exception:
            raise serializers.ValidationError("Invalid refresh token")
        return value