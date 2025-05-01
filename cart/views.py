# cart/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.core.cache import cache
from django.db.models import F
from django.conf import settings
from rest_framework.permissions import AllowAny
from .models import CartItem
from .serializers import CartItemSerializer, CartItemPagination
from account.permissions import IsCustomer
from products.tasks import send_low_stock_alert
from rest_framework import serializers

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [AllowAny] if settings.DEBUG else [IsCustomer]
    pagination_class = CartItemPagination

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user).select_related('product__vendor')

    def perform_create(self, serializer):
        with transaction.atomic():
            product = serializer.validated_data['product']
            quantity = serializer.validated_data['quantity']
            # Lock product row
            product = product.__class__.objects.select_for_update().select_related('vendor').get(id=product.id)
            if product.stock < quantity:
                raise serializers.ValidationError(f"Insufficient stock: {product.stock} available")
            product.stock = F('stock') - quantity
            product.save()
            serializer.save(user=self.request.user)
            # Invalidate caches
            cache.delete(f"product_{product.id}")
            cache.delete(f"cart_items_{self.request.user.id}")
            # Check for low stock
            if product.is_low_stock:
                send_low_stock_alert.delay(product.vendor.id, [product.id])

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = self.get_object()
            product = instance.product
            # Lock product row
            product = product.__class__.objects.select_for_update().select_related('vendor').get(id=product.id)
            new_quantity = serializer.validated_data.get('quantity', instance.quantity)
            stock_diff = new_quantity - instance.quantity
            if stock_diff > product.stock:
                raise serializers.ValidationError(f"Insufficient stock: {product.stock} available")
            product.stock = F('stock') - stock_diff
            product.save()
            serializer.save()
            # Invalidate caches
            cache.delete(f"product_{product.id}")
            cache.delete(f"cart_items_{self.request.user.id}")
            # Check for low stock
            if product.is_low_stock:
                send_low_stock_alert.delay(product.vendor.id, [product.id])

    def perform_destroy(self, instance):
        with transaction.atomic():
            product = instance.product
            # Lock product row
            product = product.__class__.objects.select_for_update().select_related('vendor').get(id=product.id)
            product.stock = F('stock') + instance.quantity
            product.save()
            instance.delete()
            # Invalidate caches
            cache.delete(f"product_{product.id}")
            cache.delete(f"cart_items_{self.request.user.id}")
            # Check for low stock
            if product.is_low_stock:
                send_low_stock_alert.delay(product.vendor.id, [product.id])

    @action(detail=False, methods=['get'])
    def total(self, request):
        cache_key = f"cart_total_{request.user.id}"
        total = cache.get(cache_key)
        if total is None:
            cart_items = self.get_queryset()
            total = sum(item.product.price * item.quantity for item in cart_items)
            cache.set(cache_key, total, 60 * 15)
        return Response({'total': total})