from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static

# Import all views
from account.views import (
    CustomerRegisterView,
    VendorRegisterView,
    AdminRegisterView,
    LoginView,
    VerifyOTPView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    LogoutView
)
from products.views import ProductViewSet, PromotionViewSet, CategoryViewSet
from sliders.views import SliderViewSet
from cart.views import CartItemViewSet
from orders.views import OrderViewSet
from reviews.views import CustomerReviewViewSet, VendorReviewViewSet
from chat.views import AdminChatViewSet, RegularChatViewSet
from profiles.views import ProfileViewSet, VendorProfileViewSet

# Initialize the DefaultRouter
router = DefaultRouter()

# Product-related endpoints
router.register(r'products', ProductViewSet, basename='products')
router.register(r'promotions', PromotionViewSet, basename='promotions')
router.register(r'categories', CategoryViewSet, basename='categories')

# Shopping cart endpoints
router.register(r'cart', CartItemViewSet, basename='cart')

# Order management endpoints
router.register(r'orders', OrderViewSet, basename='orders')

# Review endpoints
router.register(r'reviews', CustomerReviewViewSet, basename='reviews')
router.register(r'vendor-reviews', VendorReviewViewSet, basename='vendor-reviews')

# Profile endpoints
router.register(r'profiles', ProfileViewSet, basename='profiles')
router.register(r'vendor-profiles', VendorProfileViewSet, basename='vendor-profiles')

# Slider endpoints
router.register(r'sliders', SliderViewSet, basename='sliders')

# Chat endpoints
router.register(r'admin-chat', AdminChatViewSet, basename='admin-chat')
router.register(r'regular-chat', RegularChatViewSet, basename='regular-chat')

# Authentication URL patterns (not using ViewSets)
auth_urlpatterns = [
    path('register/customer/', CustomerRegisterView.as_view(), name='customer-register'),
    path('register/vendor/', VendorRegisterView.as_view(), name='vendor-register'),
    path('register/admin/', AdminRegisterView.as_view(), name='admin-register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

# Main URL patterns
urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include([
        # Authentication endpoints
        path('auth/', include(auth_urlpatterns)),
        
        # All other API endpoints from router
        path('', include(router.urls)),
    ])),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)