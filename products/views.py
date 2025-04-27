# products/views.py (unchanged, for reference)
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from .models import Product, Promotion
from .serializers import ProductSerializer, PromotionSerializer, ProductPagination
from orders.models import OrderItem
from orders.serializers import OrderItemSerializer
from account.permissions import IsApprovedVendor

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'vendor')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = ProductPagination

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'low_stock', 'vendor_dashboard', 'vendor_orders']:
            return [IsApprovedVendor()]
        return super().get_permissions()

    def get_queryset(self):
        return super().get_queryset().select_related('category', 'vendor')

    @cache_page(60 * 15)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)
        cache.delete(f"product_{serializer.instance.id}")
        cache.delete(f"products_list_{self.request.user.id}")

    def perform_update(self, serializer):
        serializer.save()
        cache.delete(f"product_{serializer.instance.id}")
        cache.delete(f"products_list_{self.request.user.id}")

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def low_stock(self, request):
        cache_key = f"low_stock_{request.user.id}"
        low_stock_products = cache.get(cache_key)
        if not low_stock_products:
            if request.user.role != 'vendor':
                return Response({"detail": "Only vendors can access this"}, status=403)
            low_stock_products = Product.objects.low_stock(request.user)
            if low_stock_products.exists():
                from .tasks import send_low_stock_alert
                send_low_stock_alert.delay(request.user.id, list(low_stock_products.values_list('id', flat=True)))
            serializer = ProductSerializer(low_stock_products, many=True)
            low_stock_products = serializer.data
            cache.set(cache_key, low_stock_products, 60 * 15)
        return Response(low_stock_products)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def vendor_dashboard(self, request):
        cache_key = f"vendor_dashboard_{request.user.id}"
        stats = cache.get(cache_key)
        if not stats:
            if request.user.role != 'vendor':
                return Response({"detail": "Only vendors can access this"}, status=403)
            products = Product.objects.filter(vendor=request.user).select_related('category')
            order_items = OrderItem.objects.filter(product__vendor=request.user)
            stats = {
                'total_products': products.count(),
                'total_sales': order_items.aggregate(total=Sum('quantity'))['total'] or 0,
                'total_revenue': order_items.aggregate(total=Sum('price_at_time'))['total'] or 0,
                'top_products': ProductSerializer(products.order_by('-sold_count')[:5], many=True).data
            }
            cache.set(cache_key, stats, 60 * 15)
        return Response(stats)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    @cache_page(60 * 15)
    def vendor_orders(self, request):
        if request.user.role != 'vendor':
            return Response({"detail": "Only vendors can access this"}, status=403)
        order_items = OrderItem.objects.filter(product__vendor=request.user).select_related('order', 'product')
        serializer = OrderItemSerializer(order_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    @cache_page(60 * 30)
    def recommendations(self, request):
        user = request.user
        wishlist_items = user.wishlist.all() if hasattr(user, 'wishlist') else []
        wishlist_categories = wishlist_items.values_list('category', flat=True).distinct()
        order_items = OrderItem.objects.filter(order__user=user)
        order_categories = order_items.values_list('product__category', flat=True).distinct()
        relevant_categories = list(wishlist_categories) + list(order_categories.difference(wishlist_categories))

        if relevant_categories:
            recommended = Product.objects.filter(
                category__in=relevant_categories,
                stock__gt=0
            ).exclude(
                id__in=wishlist_items.values_list('id', flat=True)
            ).select_related('category', 'vendor').order_by('-sold_count')[:5]
        else:
            recommended = Product.objects.filter(
                stock__gt=0, is_trending=True
            ).select_related('category', 'vendor').order_by('-sold_count')[:5]

        serializer = ProductSerializer(recommended, many=True)
        return Response(serializer.data)

class PromotionViewSet(viewsets.ModelViewSet):
    serializer_class = PromotionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'vendor':
            return Promotion.objects.filter(vendor=self.request.user)
        return Promotion.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'vendor':
            raise serializer.ValidationError("Only vendors can create promotions.")
        serializer.save(vendor=self.request.user)