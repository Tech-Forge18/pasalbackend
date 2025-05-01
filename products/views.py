# products/views.py
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.core.cache import cache
from django.conf import settings
from .models import Product, Promotion, ProductImage, Category
from .serializers import ProductSerializer, PromotionSerializer, CategorySerializer, ProductPagination
from orders.models import OrderItem
from orders.serializers import OrderItemSerializer
from account.permissions import IsApprovedVendor

logger = logging.getLogger('gurkha_pasal')

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'vendor').prefetch_related('additional_images')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = ProductPagination

    def get_permissions(self):
        if settings.DEBUG:
            # Allow any permission during development when DEBUG is True
            return [permissions.AllowAny()]
        
        # Apply custom permissions for certain actions in production
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'low_stock', 'vendor_dashboard', 'vendor_orders', 'add_image']:
            return [IsApprovedVendor()]

        return super().get_permissions()

    def get_queryset(self):
        return super().get_queryset().select_related('category', 'vendor').prefetch_related('additional_images')

    def list(self, request, *args, **kwargs):
        cache_key = "product_list"
        cached_products = cache.get(cache_key)
        if not cached_products:
            products = self.get_queryset()
            serializer = self.get_serializer(products, many=True)
            cached_products = serializer.data
            cache.set(cache_key, cached_products, 60 * 15)
            logger.info("Product list cached")
        return Response(cached_products)

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)
        cache.delete(f"product_{serializer.instance.id}")
        cache.delete(f"products_list_{self.request.user.id}")
        cache.delete("product_list")
        logger.info(f"Product {serializer.instance.name} created by {self.request.user.username}")

    def perform_update(self, serializer):
        serializer.save()
        cache.delete(f"product_{serializer.instance.id}")
        cache.delete(f"products_list_{self.request.user.id}")
        cache.delete("product_list")
        logger.info(f"Product {serializer.instance.name} updated by {self.request.user.username}")

    @action(detail=True, methods=['get','post'], permission_classes=[permissions.IsAuthenticated])
    def add_image(self, request, pk=None):
        product = self.get_object()
        if product.vendor != request.user:
            return Response({"detail": "You can only add images to your own products"}, status=status.HTTP_403_FORBIDDEN)
        image = request.FILES.get('image')
        if not image:
            return Response({"detail": "Image is required"}, status=status.HTTP_400_BAD_REQUEST)
        ProductImage.objects.create(product=product, image=image)
        cache.delete(f"product_{product.id}")
        cache.delete("product_list")
        logger.info(f"Image added to product {product.name} by {request.user.username}")
        return Response({"detail": "Image added successfully"}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def low_stock(self, request):
        cache_key = f"low_stock_{request.user.id}"
        low_stock_products = cache.get(cache_key)
        if not low_stock_products:
            if request.user.role != 'vendor':
                return Response({"detail": "Only vendors can access this"}, status=status.HTTP_403_FORBIDDEN)
            low_stock_products = Product.objects.low_stock(request.user)
            if low_stock_products.exists():
                from .tasks import send_low_stock_alert
                send_low_stock_alert.delay(request.user.id, list(low_stock_products.values_list('id', flat=True)))
            serializer = ProductSerializer(low_stock_products, many=True)
            low_stock_products = serializer.data
            cache.set(cache_key, low_stock_products, 60 * 15)
            logger.info(f"Low stock products cached for vendor {request.user.username}")
        return Response(low_stock_products)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def vendor_dashboard(self, request):
        cache_key = f"vendor_dashboard_{request.user.id}"
        stats = cache.get(cache_key)
        if not stats:
            if request.user.role != 'vendor':
                return Response({"detail": "Only vendors can access this"}, status=status.HTTP_403_FORBIDDEN)
            products = Product.objects.filter(vendor=request.user).select_related('category')
            order_items = OrderItem.objects.filter(product__vendor=request.user)
            stats = {
                'total_products': products.count(),
                'total_sales': order_items.aggregate(total=Sum('quantity'))['total'] or 0,
                'total_revenue': order_items.aggregate(total=Sum('price_at_time'))['total'] or 0,
                'top_products': ProductSerializer(products.order_by('-sold_count')[:5], many=True).data
            }
            cache.set(cache_key, stats, 60 * 15)
            logger.info(f"Vendor dashboard cached for {request.user.username}")
        return Response(stats)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def vendor_orders(self, request):
        cache_key = f"vendor_orders_{request.user.id}"
        cached_orders = cache.get(cache_key)
        if not cached_orders:
            if request.user.role != 'vendor':
                return Response({"detail": "Only vendors can access this"}, status=status.HTTP_403_FORBIDDEN)
            order_items = OrderItem.objects.filter(product__vendor=request.user).select_related('order', 'product')
            serializer = OrderItemSerializer(order_items, many=True)
            cached_orders = serializer.data
            cache.set(cache_key, cached_orders, 60 * 15)
            logger.info(f"Vendor orders cached for {request.user.username}")
        return Response(cached_orders)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def recommendations(self, request):
        cache_key = f"recommendations_{request.user.id}"
        cached_recommendations = cache.get(cache_key)
        if not cached_recommendations:
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
                ).select_related('category', 'vendor').prefetch_related('additional_images').order_by('-sold_count')[:5]
            else:
                recommended = Product.objects.filter(
                    stock__gt=0, is_trending=True
                ).select_related('category', 'vendor').prefetch_related('additional_images').order_by('-sold_count')[:5]

            serializer = ProductSerializer(recommended, many=True)
            cached_recommendations = serializer.data
            cache.set(cache_key, cached_recommendations, 60 * 30)
            logger.info(f"Recommendations cached for {request.user.username}")
        return Response(cached_recommendations)

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

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related('vendor', 'parent_category').prefetch_related('subcategories')
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if settings.DEBUG:
           return []  # No permission checks in DEBUG mode
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
           return [IsApprovedVendor()]
       return super().get_permissions()

    def get_queryset(self):
        if self.request.user.role == 'vendor':
            return Category.objects.filter(vendor=self.request.user).select_related('vendor', 'parent_category').prefetch_related('subcategories')
        return Category.objects.all().select_related('vendor', 'parent_category').prefetch_related('subcategories')

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)
        logger.info(f"Category {serializer.instance.name} created by {self.request.user.username}")

    def perform_update(self, serializer):
        serializer.save()
        logger.info(f"Category {serializer.instance.name} updated by {self.request.user.username}")