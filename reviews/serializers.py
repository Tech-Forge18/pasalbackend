# reviews/serializers.py
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
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    replies = ReviewReplySerializer(many=True, read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'product', 'product_id', 'product_code', 'product_slug',
            'rating', 'comment', 'image', 'created_at', 'replies'
        ]
        read_only_fields = ['user', 'created_at', 'replies', 'product_code', 'product_slug']

    def validate(self, data):
        user = self.context['request'].user
        product = data.get('product')
        # Check if user has ordered the product
        if not Order.objects.filter(
            user=user,
            order_items__product=product,
            status__in=['processing', 'shipped', 'delivered']
        ).distinct().exists():
            raise serializers.ValidationError("You can only review products you've ordered.")
        return data