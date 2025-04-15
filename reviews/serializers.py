from rest_framework import serializers
from .models import Review, ReviewReply
from products.models import Product
from products.serializers import ProductSerializer
from orders.models import Order, OrderItem

class ReviewReplySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ReviewReply
        fields = ['id', 'user', 'comment', 'created_at']
        read_only_fields = ['user', 'created_at']

class ReviewSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    user = serializers.StringRelatedField(read_only=True)
    replies = ReviewReplySerializer(many=True, read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)  # Add image field

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'product_id', 'rating', 'comment', 'image', 'created_at', 'replies']
        read_only_fields = ['user', 'created_at', 'replies']

    def validate(self, data):
        user = self.context['request'].user
        product = data.get('product')
        # Check if user has ordered the product
        if not Order.objects.filter(
            user=user,
            order_items__product=product,
            status__in=['processing', 'shipped', 'delivered']
        ).exists():
            raise serializers.ValidationError("You can only review products you've ordered.")
        return data