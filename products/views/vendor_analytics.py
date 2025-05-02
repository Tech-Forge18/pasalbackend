# products/views/vendor_analytics.py
import logging
from django.core.cache import cache
from django.db.models import Sum
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from orders.models import OrderItem
from products.models import Product
from products.serializers import ProductSerializer
from orders.serializers import OrderItemSerializer

logger = logging.getLogger('gurkha_pasal')

class VendorProductAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        if request.user.role != 'vendor':
            return Response({"detail": "Only vendors can access this"}, status=403)
        cache_key = f"low_stock_{request.user.id}"
        low_stock = cache.get(cache_key)
        if not low_stock:
            low_stock_qs = Product.objects.low_stock(request.user)
            if low_stock_qs.exists():
                from products.tasks import send_low_stock_alert
                send_low_stock_alert.delay(request.user.id, list(low_stock_qs.values_list('id', flat=True)))
            serializer = ProductSerializer(low_stock_qs, many=True)
            low_stock = serializer.data
            cache.set(cache_key, low_stock, 60 * 15)
        return Response(low_stock)

    @action(detail=False, methods=['get'])
    def vendor_dashboard(self, request):
        if request.user.role != 'vendor':
            return Response({"detail": "Only vendors can access this"}, status=403)
        cache_key = f"vendor_dashboard_{request.user.id}"
        stats = cache.get(cache_key)
        if not stats:
            products = Product.objects.filter(vendor=request.user)
            order_items = OrderItem.objects.filter(product__vendor=request.user)
            stats = {
                'total_products': products.count(),
                'total_sales': order_items.aggregate(total=Sum('quantity'))['total'] or 0,
                'total_revenue': order_items.aggregate(total=Sum('price_at_time'))['total'] or 0,
                'top_products': ProductSerializer(products.order_by('-sold_count')[:5], many=True).data
            }
            cache.set(cache_key, stats, 60 * 15)
        return Response(stats)

    @action(detail=False, methods=['get'])
    def vendor_orders(self, request):
        if request.user.role != 'vendor':
            return Response({"detail": "Only vendors can access this"}, status=403)
        cache_key = f"vendor_orders_{request.user.id}"
        cached_orders = cache.get(cache_key)
        if not cached_orders:
            order_items = OrderItem.objects.filter(product__vendor=request.user)
            serializer = OrderItemSerializer(order_items, many=True)
            cached_orders = serializer.data
            cache.set(cache_key, cached_orders, 60 * 15)
        return Response(cached_orders)
