
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static


# Import all views
from account.views import (
    RegisterView, VerifyOtpView, ResendOtpView,
    LoginView, ForgotPasswordView, ResetPasswordView,
    ResendPasswordOtpView, UserView, AdminView,
    LogoutView, AdminDashboardView, VendorDashboardView
)
from products.views import ProductViewSet, PromotionViewSet, CategoryViewSet
from sliders.views import SliderViewSet
from cart.views import CartItemViewSet
from orders.views import OrderViewSet
from reviews.views import CustomerReviewViewSet, VendorReviewViewSet
from chat.views import AdminChatViewSet, RegularChatViewSet
from profiles.views import ProfileViewSet, VendorProfileViewSet

# Initialize the main router
router = DefaultRouter()


# Product-related ViewSets
router.register(r'products', ProductViewSet, basename='products')
router.register(r'promotions', PromotionViewSet, basename='promotions')
router.register(r'categories', CategoryViewSet, basename='categories')

# Other app ViewSets
router.register(r'cart', CartItemViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'reviews', CustomerReviewViewSet, basename='reviews')
router.register(r'vendor-reviews', VendorReviewViewSet, basename='vendor-reviews')
router.register(r'profiles', ProfileViewSet, basename='profiles')
router.register(r'vendor-profiles', VendorProfileViewSet, basename='vendor-profiles')
router.register(r'sliders', SliderViewSet, basename='sliders')
router.register(r'admin-chat', AdminChatViewSet, basename='admin-chat')
router.register(r'regular-chat', RegularChatViewSet, basename='regular-chat')


auth_urls = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('resend-password-otp/', ResendPasswordOtpView.as_view(), name='resend-password-otp'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]


dashboard_urls = [
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('vendor-dashboard/', VendorDashboardView.as_view(), name='vendor-dashboard'),
]

# ======================
# Main URL Patterns
# ======================
urlpatterns = [
    
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include([
       
        path('auth/', include(auth_urls)),
        
        
        path('dashboards/', include(dashboard_urls)),
        
        path('', include(router.urls)),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)