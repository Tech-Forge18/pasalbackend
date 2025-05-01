"""
URL configuration for gurkha_pasal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from account.views import RegisterView, VerifyOtpView, ResendOtpView, LoginView, ForgotPasswordView, ResetPasswordView, ResendPasswordOtpView, UserView, AdminView, LogoutView, AdminDashboardView, VendorDashboardView
from products.views import ProductViewSet, PromotionViewSet, CategoryViewSet
from sliders.views import SliderViewSet
from cart.views import CartItemViewSet
from orders.views import OrderViewSet
from reviews.views import CustomerReviewViewSet, VendorReviewViewSet
from django.conf import settings
from django.conf.urls.static import static
from chat.views import AdminChatViewSet, RegularChatViewSet
from profiles.views import ProfileViewSet, VendorProfileViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'cart', CartItemViewSet, basename='cart_item')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'reviews', CustomerReviewViewSet, basename='customer-review')
router.register(r'vendor-reviews', VendorReviewViewSet, basename='vendor-review')

router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'vendor-profiles', VendorProfileViewSet, basename='vendor-profile')

router.register(r'sliders', SliderViewSet, basename='slider')
router.register(r'admin-chat', AdminChatViewSet, basename='admin-chat')
router.register(r'regular-chat', RegularChatViewSet, basename='regular-chat')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include((router.urls, 'api'), namespace='api')),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('resend-password-otp/', ResendPasswordOtpView.as_view(), name='resend-password-otp'),
    path('user/', UserView.as_view(), name='user'),
    path('admin/', AdminView.as_view(), name='admin'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('vendor-dashboard/', VendorDashboardView.as_view(), name='vendor-dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


    