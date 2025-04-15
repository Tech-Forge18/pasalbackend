# cart/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import CartItem
from .serializers import CartItemSerializer, CartItemPagination
from account.permissions import IsCustomer
from products.tasks import send_low_stock_alert

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsCustomer]
    pagination_class = CartItemPagination

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user).select_related('product__vendor')

    def perform_create(self, serializer):
        with transaction.atomic():
            product = serializer.validated_data['product']
            quantity = serializer.validated_data['quantity']
            product = product.__class__.objects.select_related('vendor').get(id=product.id)
            if product.stock < quantity:
                raise serializer.ValidationError(f"Insufficient stock: {product.stock} available")
            product.stock -= quantity
            product.save()
            serializer.save(user=self.request.user)
            # Check for low stock
            if product.is_low_stock:
                send_low_stock_alert.delay(product.vendor.id, [product.id])

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = self.get_object()
            product = instance.product
            product = product.__class__.objects.select_related('vendor').get(id=product.id)
            new_quantity = serializer.validated_data.get('quantity', instance.quantity)
            stock_diff = new_quantity - instance.quantity
            if stock_diff > product.stock:
                raise serializer.ValidationError(f"Insufficient stock: {product.stock} available")
            product.stock -= stock_diff
            product.save()
            serializer.save()
            # Check for low stock
            if product.is_low_stock:
                send_low_stock_alert.delay(product.vendor.id, [product.id])

    def perform_destroy(self, instance):
        with transaction.atomic():
            product = instance.product
            product = product.__class__.objects.select_related('vendor').get(id=product.id)
            product.stock += instance.quantity
            product.save()
            instance.delete()
            # Check for low stock (in case restocking doesn't resolve it)
            if product.is_low_stock:
                send_low_stock_alert.delay(product.vendor.id, [product.id])

    @action(detail=False, methods=['get'])
    def total(self, request):
        cart_items = self.get_queryset()
        total = sum(item.product.price * item.quantity for item in cart_items)
        return Response({'total': total})