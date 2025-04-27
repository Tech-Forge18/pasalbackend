# profile/serializers.py
from rest_framework import serializers
from .models import Profile, VendorProfile
from products.models import Product
from products.serializers import ProductSerializer

class VendorProfileSerializer(serializers.ModelSerializer):
    full_address = serializers.ReadOnlyField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = VendorProfile
        fields = ['store_name', 'store_logo', 'address_line1', 'address_line2', 'city',
                  'state', 'postal_code', 'country', 'contact_email', 'full_address', 'created_at', 'updated_at', 'is_following']
        read_only_fields = ['created_at', 'updated_at']

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'customer':
            try:
                profile = Profile.objects.get(user=request.user)
                return profile.followed_stores.filter(id=obj.id).exists()
            except Profile.DoesNotExist:
                return False
        return False

class ProfileSerializer(serializers.ModelSerializer):
    wishlist = ProductSerializer(many=True, read_only=True)
    followed_stores = VendorProfileSerializer(many=True, read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True, required=False
    )

    class Meta:
        model = Profile
        fields = ['bio', 'phone_number', 'profile_picture', 'wishlist', 'product_id', 'followed_stores', 'created_at', 'updated_at']
        read_only_fields = ['wishlist', 'followed_stores', 'created_at', 'updated_at']

    def validate(self, data):
        user = self.context['request'].user
        if self.instance and self.instance.user != user:
            raise serializers.ValidationError("You can only update your own profile")
        return data