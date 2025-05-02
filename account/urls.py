from django.urls import path
from .views import (
    CustomerRegisterView,
    VendorRegisterView,
    AdminRegisterView,
    LoginView,
    VerifyOTPView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    LogoutView
)

urlpatterns = [
    path('register/customer/', CustomerRegisterView.as_view(), name='customer-register'),
    path('register/vendor/', VendorRegisterView.as_view(), name='vendor-register'),
    path('register/admin/', AdminRegisterView.as_view(), name='admin-register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('logout/', LogoutView.as_view(), name='logout'),
]