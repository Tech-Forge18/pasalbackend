from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import jwt

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
    def validate(self, attrs):
        credentials = {'password': attrs.get('password')}
        user_input = attrs.get('username')
        
        if '@' in user_input:
            credentials['email'] = user_input
        else:
            credentials['username'] = user_input
        
        user = authenticate(**credentials)
        
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        
        if not user.is_verified:
            raise serializers.ValidationError("Account not verified. Please check your OTP.")
        
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