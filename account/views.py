# account/views.py
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.conf import settings
from django_ratelimit.decorators import ratelimit
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer, UserLoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer, LogoutSerializer
from .permissions import IsCustomer, IsApprovedVendor, IsAdmin
from orders.models import Order
from orders.serializers import OrderSerializer
from utils.mail import send_mailersend_email

logger = logging.getLogger('gurkha_pasal')

class UserViewSet(viewsets.ViewSet):
    """ViewSet for user authentication (signup, login, logout, forgot password)."""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        logger.info(f"User {user.username} registered with role {user.role}")
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    @ratelimit(key='ip', rate='5/m', method='POST', block=True)
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        refresh = RefreshToken.for_user(user)
        logger.info(f"User {user.username} logged in")
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate signed token (valid for 24 hours)
        signer = TimestampSigner()
        token = signer.sign(user.username)
        
        # Send reset email
        reset_url = f"{settings.FRONTEND_URL}/reset-password/?token={token}"
        subject = "Password Reset Request - Gurkha Pasal"
        message = f"""
Dear {user.username},

You requested a password reset. Click the link below to reset your password:

{reset_url}

This link is valid for 24 hours. If you did not request this, please ignore this email.

Best regards,
Gurkha Pasal Team
"""
        try:
            send_mailersend_email.delay(email, subject, message)
            logger.info(f"Password reset email sent to {user.username}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.username}: {str(e)}")
            return Response({"detail": "Failed to send email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({"detail": "Password reset email sent"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        
        # Verify token
        signer = TimestampSigner()
        try:
            username = signer.unsign(token, max_age=24*3600)  # 24 hours
            user = User.objects.get(username=username)
        except (SignatureExpired, BadSignature, User.DoesNotExist):
            return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update password
        user.set_password(password)
        user.save()
        logger.info(f"Password reset for {user.username}")
        return Response({"detail": "Password reset successful"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data['refresh']
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"User {request.user.username} logged out, refresh token blacklisted")
            return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to blacklist refresh token for {request.user.username}: {str(e)}")
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)

class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for customer user management."""
    serializer_class = UserSerializer
    permission_classes = [IsCustomer]
    lookup_field = 'username'
    queryset = User.objects.filter(role='customer')

    def get_object(self):
        username = self.kwargs.get(self.lookup_field)
        return get_object_or_404(self.queryset, username=username)

    def list(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    def retrieve(self, request, username=None):
        customer = self.get_object()
        if request.user != customer:
            self.check_object_permissions(request, customer)
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def orders(self, request):
        orders = request.user.orders.all()
        return Response(OrderSerializer(orders, many=True).data)

class VendorViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor user management."""
    serializer_class = UserSerializer
    permission_classes = [IsApprovedVendor]
    queryset = User.objects.filter(role='vendor')

class AdminViewSet(viewsets.ModelViewSet):
    """ViewSet for admin user management."""
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.filter(role='admin')