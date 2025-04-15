from rest_framework import serializers
from .models import Profile, VendorProfile
from products.models import Product
from products.serializers import ProductSerializer

class ProfileSerializer(serializers.ModelSerializer):
    wishlist = ProductSerializer(many=True, read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = Profile
        fields = ['bio', 'phone_number', 'profile_picture', 'wishlist', 'product_id']

class VendorProfileSerializer(serializers.ModelSerializer):
    full_address = serializers.ReadOnlyField()

    class Meta:
        model = VendorProfile
        fields = ['store_name', 'store_logo', 'address_line1', 'address_line2', 'city', 
                  'state', 'postal_code', 'country', 'contact_email', 'full_address']