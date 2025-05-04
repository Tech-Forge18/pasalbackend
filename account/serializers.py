
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email  # Import validate_email here

import jwt
import logging

logger = logging.getLogger(__name__)

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone_number']

    def create(self, validated_data):
        role = self.context.get('role', 'customer')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number'),
            role=role
        )
        otp = user.generate_otp()
        self.send_otp_email(user.email, otp)
        return user

    def send_otp_email(self, email, otp):
        send_mail(
            'Your OTP Code',
            f'Your verification code is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        logger.debug(f"Login attempt with email: {email}")

        # Check for missing email
        if not email:
            raise serializers.ValidationError({"email": "Email is required."})

        # Validate email format
        try:
            validate_email(email)
        except DjangoValidationError:
            raise serializers.ValidationError({"email": "Enter a valid email address."})

        # Check if user with the email exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "Email does not exist."})

        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Incorrect password."})

        # Check if user is verified
        if not user.is_verified:
            raise serializers.ValidationError({
                "non_field_errors": ["Account not verified. Please check your OTP."]
            })

        # Generate JWT tokens
        refresh = self.get_token(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'role': user.role,
            'email': user.email
        }
class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()