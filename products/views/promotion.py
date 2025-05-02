# products/views/promotion.py
from rest_framework import viewsets, permissions
from django.core.cache import cache
from rest_framework.response import Response
from products.models import Promotion
from products.serializers import PromotionSerializer

class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        cache_key = "promotion_list"
        promotions = cache.get(cache_key)
        if not promotions:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            promotions = serializer.data
            cache.set(cache_key, promotions, 60 * 15)
        return Response(promotions)
