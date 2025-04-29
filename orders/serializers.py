# orders/serializers.py
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from .models import Order, ShippingAddress, OrderItem
from .constants import STATUS_CHOICES
from products.models import Product
from products.serializers import ProductSerializer
from products.models import Promotion  # Assuming you have a Promotion model


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = ['id', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'is_default']
        read_only_fields = ['user']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    selected_color = serializers.CharField(required=False, allow_blank=True)
    selected_size = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_id', 'product_code', 'product_slug', 'quantity',
            'price_at_time', 'selected_color', 'selected_size', 'status'
        ]
        read_only_fields = ['price_at_time', 'product_code', 'product_slug']

    def validate(self, data):
        product = Product.objects.select_related('vendor').get(id=data['product'].id)
        quantity = data.get('quantity', 1)
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        if product.stock < quantity:
            raise serializers.ValidationError(f"Not enough stock for {product.name}")
        selected_color = data.get('selected_color')
        selected_size = data.get('selected_size')
        if product.color and not selected_color:
            raise serializers.ValidationError("Please select a color")
        if product.sizes and not selected_size:
            raise serializers.ValidationError("Please select a size")
        if selected_color and selected_color not in product.color:
            raise serializers.ValidationError(f"Invalid color: {selected_color}")
        if selected_size and selected_size not in product.sizes:
            raise serializers.ValidationError(f"Invalid size: {selected_size}")
        return data


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True)  # Renamed from cart_items
    shipping_address = serializers.PrimaryKeyRelatedField(
        queryset=ShippingAddress.objects.all(), allow_null=True
    )
    promotion_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = ['id', 'user', 'shipping_address', 'total_amount', 'status', 'created_at', 'order_items', 'promotion_code']
        read_only_fields = ['user', 'total_amount', 'status', 'created_at']

    def validate(self, data):
        order_items = data.get('order_items', [])
        if not order_items:
            raise serializers.ValidationError("At least one item is required")
        shipping_address = data.get('shipping_address')
        if not shipping_address:
            raise serializers.ValidationError("Shipping address is required")
        return data

    def create(self, validated_data):
        order_items_data = validated_data.pop('order_items')
        promotion_code = validated_data.get('promotion_code')
        order = Order.objects.create(
            user=self.context['request'].user,
            shipping_address=validated_data.get('shipping_address'),
            total_amount=0
        )
        total_amount = 0
        for item_data in order_items_data:
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

        # Check if promotion code is provided and valid
        if promotion_code:
            try:
                # Check if the promotion code is valid for the user
                promotion = Promotion.objects.get(code=promotion_code, vendor=self.context['request'].user)
                if promotion.is_active():
                    # Apply promotion if it belongs to the correct vendor and is active
                    discount = total_amount * (promotion.discount_percent / 100)
                    total_amount -= discount
                else:
                    raise serializers.ValidationError("Promotion code is not active or invalid.")
            except Promotion.DoesNotExist:
                raise serializers.ValidationError("Invalid promotion code.")

        order.total_amount = total_amount
        order.save()
        return order


class OrderPagination(PageNumberPagination):
    page_size = 10
