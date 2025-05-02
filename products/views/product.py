# products/views/product.py
import logging
from rest_framework.decorators import action
from rest_framework import viewsets, permissions
from django.core.cache import cache
from django.conf import settings
from ..models import Product
from ..serializers import ProductSerializer, ProductPagination
from account.permissions import IsVendor

logger = logging.getLogger('gurkha_pasal')

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'vendor').prefetch_related('additional_images')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = ProductPagination

    def get_permissions(self):
        if settings.DEBUG:
            return [permissions.AllowAny()]
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'add_image']:
            return [IsApprovedVendor()]
        return super().get_permissions()

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
        cache.delete("product_list")
        logger.info(f"Product {serializer.instance.name} created by {self.request.user.username}")

    def perform_update(self, serializer):
        serializer.save()
        cache.delete("product_list")
        logger.info(f"Product {serializer.instance.name} updated by {self.request.user.username}")

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_image(self, request, pk=None):
        product = self.get_object()
        if product.vendor != request.user:
            return Response({"detail": "Not allowed"}, status=403)
        image = request.FILES.get('image')
        if not image:
            return Response({"detail": "Image is required"}, status=400)
        from .models import ProductImage
        ProductImage.objects.create(product=product, image=image)
        cache.delete("product_list")
        return Response({"detail": "Image added"}, status=201)
