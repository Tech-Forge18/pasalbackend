from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken, BlacklistMixin
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from .models import User
from .serializers import *
from .throttles import *
from .permissions import *

class AuthView(APIView):
    throttle_classes = [LoginThrottle]

    def post(self, request, action):
        if action == 'login':
            return self._handle_login(request)
        elif action == 'register':
            return self._handle_register(request)
        elif action == 'verify-otp':
            return self._verify_otp(request)
        return Response(
            {'error': 'Invalid action'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    def _handle_login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })

    def _handle_register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        otp = get_random_string(6, '0123456789')
        cache.set(f'reg_otp_{email}', otp, 300)
        cache.set(f'reg_data_{email}', serializer.validated_data, 300)

        send_mail(
            'Registration OTP',
            f'Your OTP code is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False
        )
        return Response({'message': 'OTP sent to email'})

    def _verify_otp(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        cached_otp = cache.get(f'reg_otp_{email}')
        if not cached_otp or cached_otp != otp:
            return Response(
                {'error': 'Invalid OTP'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user_data = cache.get(f'reg_data_{email}')
        if not user_data:
            return Response(
                {'error': 'Session expired'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = RegisterSerializer(data=user_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        cache.delete_many([f'reg_otp_{email}', f'reg_data_{email}'])
        return Response(
            {'message': 'Account created successfully'},
            status=status.HTTP_201_CREATED
        )

class PasswordResetView(APIView):
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        if 'otp' not in serializer.validated_data:
            return self._send_otp(email)
        return self._reset_password(email, serializer.validated_data)

    def _send_otp(self, email):
        otp = get_random_string(6, '0123456789')
        cache.set(f'pwd_otp_{email}', otp, 300)
        
        send_mail(
            'Password Reset OTP',
            f'Your OTP code is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False
        )
        return Response({'message': 'OTP sent to email'})

    def _reset_password(self, email, data):
        cached_otp = cache.get(f'pwd_otp_{email}')
        if not cached_otp or cached_otp != data['otp']:
            return Response(
                {'error': 'Invalid OTP'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user = User.objects.get(email=email)
        user.set_password(data['new_password'])
        user.save()
        
        cache.delete(f'pwd_otp_{email}')
        return Response({'message': 'Password updated successfully'})

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class AdminView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )