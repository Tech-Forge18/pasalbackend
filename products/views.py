# products/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, F
from .models import Product, Promotion
from .serializers import ProductSerializer, PromotionSerializer, ProductPagination
from orders.models import OrderItem
from orders.serializers import OrderItemSerializer
from django.views.decorators.cache import cache_page

class IsVendor(permissions.BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'role') and request.user.role == 'vendor'

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'vendor')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = ProductPagination

    def get_queryset(self):
        return super().get_queryset().select_related('category', 'vendor')

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    @cache_page(60 * 15)
    def low_stock(self, request):
        if request.user.role != 'vendor':
            return Response({"detail": "Only vendors can access this"}, status=403)
        low_stock_products = Product.objects.low_stock(request.user)
        if low_stock_products.exists():
            from .tasks import send_low_stock_alert
            send_low_stock_alert.delay(request.user.id, list(low_stock_products.values_list('id', flat=True)))
        serializer = ProductSerializer(low_stock_products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    @cache_page(60 * 15)
    def vendor_dashboard(self, request):
        if request.user.role != 'vendor':
            return Response({"detail": "Only vendors can access this"}, status=403)
        products = Product.objects.filter(vendor=request.user).select_related('category')
        order_items = OrderItem.objects.filter(product__vendor=request.user)
        stats = {
            'total_products': products.count(),
            'total_sales': order_items.aggregate(Sum('quantity'))['quantity__sum'] or 0,
            'total_revenue': order_items.aggregate(Sum('price_at_time'))['price_at_time__sum'] or 0,
            'top_products': ProductSerializer(products.order_by('-sold_count')[:5], many=True).data
        }
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
    @cache_page(60 * 15)
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