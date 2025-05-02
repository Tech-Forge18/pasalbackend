from rest_framework.routers import DefaultRouter
from products.views.product import ProductViewSet
from products.views.vendor_analytics import VendorProductAnalyticsViewSet
from products.views.recommendation import RecommendationViewSet
from products.views.promotion import PromotionViewSet
from products.views.category import CategoryViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')

router.register(r'vendor-analytics', VendorProductAnalyticsViewSet, basename='vendor-analytics')
router.register(r'recommendations', RecommendationViewSet, basename='recommendations')
router.register(r'promotions', PromotionViewSet, basename='promotions')
router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
]