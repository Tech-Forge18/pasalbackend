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
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    selected_color = serializers.CharField(required=False, allow_blank=True)
    selected_size = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'user', 'product', 'product_id', 'product_code', 'product_slug',
            'quantity', 'selected_color', 'selected_size', 'added_at'
        ]
        read_only_fields = ['id', 'user', 'added_at', 'product_code', 'product_slug']

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        selected_color = data.get('selected_color')
        selected_size = data.get('selected_size')
        # Require color/size if product has variants
        if product.color and not selected_color:
            raise serializers.ValidationError("Please select a color")
        if product.sizes and not selected_size:
            raise serializers.ValidationError("Please select a size")
        # Validate selected variants
        if selected_color and selected_color not in product.color:
            raise serializers.ValidationError(f"Invalid color: {selected_color}")
        if selected_size and selected_size not in product.sizes:
            raise serializers.ValidationError(f"Invalid size: {selected_size}")
        return data

class CartItemPagination(PageNumberPagination):
    page_size = 10