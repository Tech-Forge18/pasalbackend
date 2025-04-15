# orders/serializers.py
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from .models import Order, ShippingAddress, OrderItem
from products.models import Product
from cart.models import CartItem

class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = ['id', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'is_default']
        read_only_fields = ['user']

class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    selected_color = serializers.CharField(required=False, allow_blank=True)
    selected_size = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price_at_time', 'selected_color', 'selected_size', 'status']

    def validate(self, data):
        product = data['product']
        quantity = data.get('quantity', 1)
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        if product.stock < quantity:
            raise serializers.ValidationError(f"Not enough stock for {product.name}")
        selected_color = data.get('selected_color')
        selected_size = data.get('selected_size')
        if selected_color and selected_color not in product.color:
            raise serializers.ValidationError(f"Invalid color: {selected_color}")
        if selected_size and selected_size not in product.sizes:
            raise serializers.ValidationError(f"Invalid size: {selected_size}")
        return data

class OrderSerializer(serializers.ModelSerializer):
    cart_items = OrderItemSerializer(many=True, source='order_items')
    shipping_address = serializers.PrimaryKeyRelatedField(
        queryset=ShippingAddress.objects.all(), allow_null=True
    )

    class Meta:
        model = Order
        fields = ['id', 'user', 'shipping_address', 'total_amount', 'status', 'created_at', 'cart_items']
        read_only_fields = ['user', 'total_amount', 'status', 'created_at']

    def validate(self, data):
        cart_items = data.get('order_items', [])
        if not cart_items:
            raise serializers.ValidationError("At least one item is required")
        shipping_address = data.get('shipping_address')
        if not shipping_address:
            raise serializers.ValidationError("Shipping address is required")
        return data

    def create(self, validated_data):
        cart_items_data = validated_data.pop('order_items')
        order = Order.objects.create(
            user=self.context['request'].user,
            shipping_address=validated_data.get('shipping_address'),
            total_amount=0
        )
        total_amount = 0
        for item_data in cart_items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            total_amount += product.price * quantity
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price_at_time=product.price,
                selected_color=item_data.get('selected_color'),
                selected_size=item_data.get('selected_size')
            )
        order.total_amount = total_amount
        order.save()
        return order

class OrderPagination(PageNumberPagination):
    page_size = 10