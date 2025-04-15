# cart/serializers.py
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from .models import CartItem
from products.serializers import ProductSerializer
from products.models import Product

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    selected_color = serializers.CharField(required=False, allow_blank=True)
    selected_size = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CartItem
        fields = ['id', 'user', 'product', 'product_id', 'quantity', 'selected_color', 'selected_size', 'added_at']
        read_only_fields = ['id', 'user', 'added_at']

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        if product.stock < quantity:
            raise serializers.ValidationError(f"Insufficient stock: {product.stock} available")
        selected_color = data.get('selected_color')
        selected_size = data.get('selected_size')
        if selected_color and selected_color not in product.color:
            raise serializers.ValidationError(f"Invalid color: {selected_color}")
        if selected_size and selected_size not in product.sizes:
            raise serializers.ValidationError(f"Invalid size: {selected_size}")
        return data

class CartItemPagination(PageNumberPagination):
    page_size = 10