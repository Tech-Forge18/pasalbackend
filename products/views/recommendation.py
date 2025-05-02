# products/views/recommendation.py
import logging
from django.core.cache import cache
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from orders.models import OrderItem
from products.models import Product
from products.serializers import ProductSerializer

logger = logging.getLogger('gurkha_pasal')

class RecommendationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        user = request.user
        cache_key = f"recommendations_{user.id}"
        cached_data = cache.get(cache_key)
        if not cached_data:
            wishlist = user.wishlist.all() if hasattr(user, 'wishlist') else []
            wishlist_categories = wishlist.values_list('category', flat=True)
            order_items = OrderItem.objects.filter(order__user=user)
            order_categories = order_items.values_list('product__category', flat=True)
            relevant_categories = set(wishlist_categories) | set(order_categories)
            queryset = Product.objects.filter(category__in=relevant_categories, stock__gt=0).exclude(id__in=wishlist).order_by('-sold_count')[:5]
            if not queryset.exists():
                queryset = Product.objects.filter(stock__gt=0, is_trending=True).order_by('-sold_count')[:5]
            serializer = ProductSerializer(queryset, many=True)
            cached_data = serializer.data
            cache.set(cache_key, cached_data, 60 * 30)
        return Response(cached_data)
