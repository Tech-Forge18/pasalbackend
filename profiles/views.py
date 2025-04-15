import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from .models import Profile, VendorProfile
from .serializers import ProfileSerializer, VendorProfileSerializer
from products.models import Product
from account.permissions import IsCustomer, IsApprovedVendor  # Import custom permissions
from django.http import Http404
from django.core.cache import cache

logger = logging.getLogger('gurkha_pasal')

class ProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for customer profile actions."""
    serializer_class = ProfileSerializer
    permission_classes = [IsCustomer]
    queryset = Profile.objects.all()

    def get_object(self):
        """Ensure the profile belongs to the requesting user, or return 404 if not found."""
        try:
            profile = Profile.objects.get(user=self.request.user)
        except Profile.DoesNotExist:
            raise Http404("Profile not found for this user")
        return profile

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get or update the authenticated customer's profile."""
        profile = self.get_object()
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(self.get_serializer(profile).data)

    @action(detail=False, methods=['post'])
    def add_to_wishlist(self, request):
        """Add a product to the customer's wishlist."""
        profile = self.get_object()
        product_id = request.data.get('product_id')
        try:
            product = get_object_or_404(Product, id=product_id)
            profile.wishlist.add(product)
            logger.info(f"Customer {request.user.username} added {product.name} to wishlist")
            return Response({"detail": "Product added to wishlist"}, status=status.HTTP_201_CREATED)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['delete'])
    def remove_from_wishlist(self, request):
        """Remove a product from the customer's wishlist."""
        profile = self.get_object()
        product_id = request.data.get('product_id')
        try:
            product = get_object_or_404(Product, id=product_id)
            profile.wishlist.remove(product)
            logger.info(f"Customer {request.user.username} removed {product.name} from wishlist")
            return Response({"detail": "Product removed from wishlist"}, status=status.HTTP_204_NO_CONTENT)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)


class VendorProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor profile actions."""
    serializer_class = VendorProfileSerializer
    permission_classes = [IsApprovedVendor]
    queryset = VendorProfile.objects.all()

    def get_object(self):
        """Ensure the vendor profile belongs to the requesting user, or return 404 if not found."""
        try:
            profile = VendorProfile.objects.get(user=self.request.user)
        except VendorProfile.DoesNotExist:
            raise Http404("Vendor profile not found for this user")
        return profile

    @action(detail=False, methods=['get', 'patch'])
    @method_decorator(cache_page(60 * 15))  # Caching for vendor profile for 15 minutes
    def me(self, request):
        """Get or update the authenticated vendor's profile."""
        profile = self.get_object()
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(self.get_serializer(profile).data)


#"Created ProfileViewSet for customers with me, add_to_wishlist, and remove_from_wishlist.
#Created VendorProfileViewSet for vendors with me.
#Renamed profile action to me for consistency (e.g., /api/profiles/me/ instead of /api/customers/profile/).
#Used IsCustomer and IsApprovedVendor permissions from account.permissions.