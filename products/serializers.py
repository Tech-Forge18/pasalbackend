# products/serializers.py
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Product, Category, Promotion

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'vendor']

class ProductSerializer(serializers.ModelSerializer):
    is_new_arrival = serializers.ReadOnlyField()
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'original_price', 'discount', 'image',
            'rating', 'sold_count', 'category', 'color', 'sizes', 'is_exclusive_deal',
            'deal_end_time', 'is_trending', 'created_at', 'vendor', 'is_new_arrival',
            'stock', 'stock_threshold'
        ]

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative")
        return value

    def validate_discount(self, value):
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError("Discount must be between 0 and 100")
        return value

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'code', 'discount_percent', 'vendor', 'start_date', 'end_date', 'created_at']
        read_only_fields = ['vendor', 'created_at']

    def validate_discount_percent(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Discount percent must be between 0 and 100")
        return value

class ProductPagination(PageNumberPagination):
    page_size = 20