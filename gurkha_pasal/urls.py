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
from products.views import ProductViewSet, PromotionViewSet
from sliders.views import SliderViewSet
from cart.views import CartItemViewSet
from orders.views import OrderViewSet
from reviews.views import CustomerReviewViewSet, VendorReviewViewSet
from account.views import CustomerViewSet, VendorViewSet,AdminViewSet # New import
from django.conf import settings
from django.conf.urls.static import static
from chat.views import AdminChatViewSet, RegularChatViewSet
from profiles.views import ProfileViewSet, VendorProfileViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'cart', CartItemViewSet, basename='cart_item')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'reviews', CustomerReviewViewSet, basename='customer-review')
router.register(r'vendor-reviews', VendorReviewViewSet, basename='vendor-review')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'vendor-profiles', VendorProfileViewSet, basename='vendor-profile')
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r'admins', AdminViewSet, basename='admin')  # New endpoint
router.register(r'sliders', SliderViewSet, basename='slider')
router.register(r'admin-chat', AdminChatViewSet, basename='admin-chat')
router.register(r'regular-chat', RegularChatViewSet, basename='regular-chat')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include((router.urls, 'api'), namespace='api')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Get access/refresh tokens
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


    ##Invoke-WebRequest -Method POST -Uri "http://127.0.0.1:8000/api/token/" -Headers @{ "Content-Type" = "application/json" } -Body '{"username": "rupesh", "password": "hello@123#"}'

    #mlsn.9ea3d3139ce7b4110afa82c56d7302bca8f5541767af6bf9e791cb247710bc49