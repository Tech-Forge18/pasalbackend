# products/serializers.py
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from .models import Product, Category, Promotion, ProductImage
from account.models import User

class CategorySerializer(serializers.ModelSerializer):
    parent_category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )
    subcategories = serializers.SerializerMethodField()

    def get_subcategories(self, obj):
        subcategories = obj.subcategories.all()
        return CategorySerializer(subcategories, many=True, context=self.context).data

    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'vendor', 'parent_category', 'subcategories']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    is_new_arrival = serializers.ReadOnlyField()
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='vendor'), required=False
    )
    additional_images = ProductImageSerializer(many=True, read_only=True)
    brand = serializers.CharField(required=False, allow_blank=True)
    specification = serializers.JSONField(default=dict)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'brand', 'specification', 'price', 'original_price',
            'discount', 'image', 'rating', 'code', 'slug', 'sold_count', 'category',
            'category_id', 'color', 'sizes', 'is_exclusive_deal', 'deal_end_time', 'is_trending',
            'created_at', 'vendor', 'is_new_arrival', 'stock', 'stock_threshold', 'additional_images'
        ]
        read_only_fields = ['id', 'sold_count', 'created_at', 'rating', 'is_new_arrival']

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative")
        return value

    def validate_discount(self, value):
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError("Discount must be between 0 and 100")
        return value

    def validate_code(self, value):
        vendor = self.context['request'].user
        instance = self.instance
        if instance and instance.code == value:
            return value
        if value and Product.objects.filter(vendor=vendor, code=value).exists():
            raise serializers.ValidationError("This code is already in use for your products")
        return value

    def validate_slug(self, value):
        if value:
            if value != slugify(value):
                raise serializers.ValidationError("Slug must be URL-safe (lowercase, hyphens, no spaces)")
            instance = self.instance
            if instance and instance.slug == value:
                return value
            if Product.objects.filter(slug=value).exists():
                raise serializers.ValidationError("This slug is already in use")
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