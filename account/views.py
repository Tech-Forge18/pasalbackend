import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from .models import User
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from .throttles import LoginThrottle, PasswordResetThrottle
from .permissions import IsVendor, IsAdmin

logger = logging.getLogger('gurkha_pasal')

class RegisterView(APIView):
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        otp = get_random_string(6, '0123456789')
        cache.set(f'reg_otp_{email}', otp, 300)
        cache.set(f'reg_data_{email}', serializer.validated_data, 300)

        try:
            send_mail(
                'Registration OTP - Gurkha Pasal',
                f'Your OTP code is: {otp}. Valid for 5 minutes.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False
            )
            logger.info(f"Registration OTP sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send OTP to {email}: {str(e)}")
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'OTP sent to email'}, status=status.HTTP_200_OK)

class VerifyOtpView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        cached_otp = cache.get(f'reg_otp_{email}')
        if not cached_otp or cached_otp != otp:
            logger.warning(f"Invalid OTP attempt for {email}")
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        user_data = cache.get(f'reg_data_{email}')
        if not user_data:
            logger.warning(f"Session expired for {email}")
            return Response({'error': 'Session expired'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RegisterSerializer(data=user_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        cache.delete_many([f'reg_otp_{email}', f'reg_data_{email}'])
        logger.info(f"User {email} registered successfully")

        return Response({
            'message': 'Account created successfully',
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_201_CREATED)

class ResendOtpView(APIView):
    throttle_classes = [LoginThrottle]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            logger.warning(f"Attempt to resend OTP for existing user {email}")
            return Response({'error': 'Email already registered'}, status=status.HTTP_400_BAD_REQUEST)

        user_data = cache.get(f'reg_data_{email}')
        if not user_data:
            logger.warning(f"No pending registration for {email}")
            return Response({'error': 'No pending registration found'}, status=status.HTTP_400_BAD_REQUEST)

        otp = get_random_string(6, '0123456789')
        cache.set(f'reg_otp_{email}', otp, 300)

        try:
            send_mail(
                'Registration OTP (Resent) - Gurkha Pasal',
                f'Your new OTP code is: {otp}. Valid for 5 minutes.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False
            )
            logger.info(f"Resent registration OTP to {email}")
        except Exception as e:
            logger.error(f"Failed to resend OTP to {email}: {str(e)}")
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'New OTP sent to email'}, status=status.HTTP_200_OK)

class LoginView(APIView):
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        refresh = RefreshToken.for_user(user)
        logger.info(f"User {user.email} logged in")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_200_OK)

class ForgotPasswordView(APIView):
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        otp = get_random_string(6, '0123456789')
        cache.set(f'pwd_otp_{email}', otp, 300)

        try:
            send_mail(
                'Password Reset OTP - Gurkha Pasal',
                f'Your OTP code is: {otp}. Valid for 5 minutes.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False
            )
            logger.info(f"Password reset OTP sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset OTP to {email}: {str(e)}")
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'OTP sent to email'}, status=status.HTTP_200_OK)

class ResetPasswordView(APIView):
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        cached_otp = cache.get(f'pwd_otp_{email}')
        if not cached_otp or cached_otp != otp:
            logger.warning(f"Invalid password reset OTP attempt for {email}")
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        cache.delete(f'pwd_otp_{email}')
        logger.info(f"Password reset for {email}")

        return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)

class ResendPasswordOtpView(APIView):
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        otp = get_random_string(6, '0123456789')
        cache.set(f'pwd_otp_{email}', otp, 300)

        try:
            send_mail(
                'Password Reset OTP (Resent) - Gurkha Pasal',
                f'Your new OTP code is: {otp}. Valid for 5 minutes.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False
            )
            logger.info(f"Resent password reset OTP to {email}")
        except Exception as e:
            logger.error(f"Failed to resend password reset OTP to {email}: {str(e)}")
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'New OTP sent to email'}, status=status.HTTP_200_OK)

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
            logger.info(f"User {request.user.email} logged out")
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error(f"Logout failed for {request.user.email}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        vendors_pending_approval = User.objects.filter(role=User.Role.VENDOR, is_approved=False)
        vendors_approved = User.objects.filter(role=User.Role.VENDOR, is_approved=True)

        pending_vendors_data = UserSerializer(vendors_pending_approval, many=True)
        approved_vendors_data = UserSerializer(vendors_approved, many=True)

        return Response({
            'pending_vendors': pending_vendors_data.data,
            'approved_vendors': approved_vendors_data.data
        })

    def post(self, request):
        vendor_id = request.data.get('vendor_id')
        is_approved = request.data.get('is_approved')

        if not vendor_id or is_approved is None:
            logger.warning(f"Invalid vendor approval request by {request.user.email}")
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vendor = User.objects.get(id=vendor_id, role=User.Role.VENDOR)
        except User.DoesNotExist:
            logger.warning(f"Vendor {vendor_id} not found for approval by {request.user.email}")
            return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)

        vendor.is_approved = is_approved
        vendor.save()
        logger.info(f"Vendor {vendor.email} approval set to {is_approved} by {request.user.email}")

        return Response({'message': 'Vendor approval status updated successfully'})

class VendorDashboardView(APIView):
    permission_classes = [IsVendor]

    def get(self, request):
        if not request.user.is_approved:
            logger.warning(f"Unapproved vendor {request.user.email} attempted dashboard access")
            return Response(
                {'error': 'Your vendor account is pending approval.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Placeholder for vendor-specific data (e.g., products, orders)
        return Response({
            'message': 'Welcome to the Vendor Dashboard',
            'vendor': UserSerializer(request.user).data
        })