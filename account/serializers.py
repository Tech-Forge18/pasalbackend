from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'is_approved']
        read_only_fields = ['id', 'is_approved']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'password': {'write_only': True},
            'confirm_password': {'write_only': True},
        }

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords must match.'})
        role = data.get('role', User.Role.CUSTOMER)
        if role not in User.Role.values:
            raise serializers.ValidationError({'role': 'Invalid role.'})
        return data

    def create(self, validated_data):
        email = validated_data['email']
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'This email is already in use.'})
        validated_data.pop('confirm_password')
        role = validated_data.get('role', User.Role.CUSTOMER)
        user = User.objects.create_user(**validated_data)
        if role == User.Role.VENDOR:
            user.is_approved = False
            user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError({'detail': 'Invalid credentials.'})
        if user.role == User.Role.VENDOR and not user.is_approved:
            raise serializers.ValidationError({'detail': 'Your vendor account is pending approval.'})
        return user

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError('No user found with this email.')
        return value

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    new_password = serializers.CharField(
        min_length=8,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        style={'input_type': 'password'}
    )

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords must match.'})
        if not User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'No user found with this email.'})
        return data