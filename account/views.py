from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    VerifyOTPSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    LogoutSerializer
)
from .models import User
from django.core.mail import send_mail
from django.conf import settings
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from django.utils import timezone
from datetime import timedelta

class CustomerRegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    throttle_classes = [AnonRateThrottle]
    
    def get_serializer_context(self):
        return {'role': 'customer'}

class VendorRegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    throttle_classes = [AnonRateThrottle]
    
    def get_serializer_context(self):
        return {'role': 'vendor'}

class AdminRegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    throttle_classes = [AnonRateThrottle]
    
    def get_serializer_context(self):
        return {'role': 'admin'}

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AnonRateThrottle]

class VerifyOTPView(generics.GenericAPIView):
    serializer_class = VerifyOTPSerializer
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(
                email=serializer.validated_data['email'],
                otp=serializer.validated_data['otp']
            )
            if user.otp_created_at < timezone.now() - timedelta(minutes=5):
                return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
                
            user.is_verified = True
            user.otp = None
            user.otp_created_at = None
            user.save()
            return Response({"message": "Account verified successfully"})
        except User.DoesNotExist:
            return Response({"error": "Invalid OTP or email"}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            token = jwt.encode(
                {'user_id': user.id, 'exp': timezone.now() + timedelta(hours=1)},
                settings.SECRET_KEY,
                algorithm='HS256'
            )
            
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            send_mail(
                'Password Reset',
                f'Click to reset your password: {reset_link}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return Response({"message": "Password reset link sent"})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            payload = jwt.decode(serializer.validated_data['token'], settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password reset successful"})
        except ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidTokenError, User.DoesNotExist):
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            token = RefreshToken(serializer.validated_data['refresh_token'])
            token.blacklist()
            return Response({"message": "Successfully logged out"})
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)