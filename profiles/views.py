# profile/views.py
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from .models import Profile, VendorProfile
from .serializers import ProfileSerializer, VendorProfileSerializer
from products.models import Product
from products.serializers import ProductSerializer
from account.permissions import IsCustomer, IsApprovedVendor
from django.http import Http404
from django.core.cache import cache

logger = logging.getLogger('gurkha_pasal')

class BurstRateThrottle(UserRateThrottle):
    rate = '10/min'

class ProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for customer profile actions."""
    serializer_class = ProfileSerializer
    permission_classes = [IsCustomer]
    queryset = Profile.objects.all()

    def get_object(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
        except Profile.DoesNotExist:
            raise Http404("Profile not found for this user")
        return profile

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        profile = self.get_object()
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            cache.delete(f"profile_{request.user.id}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(self.get_serializer(profile).data)

    @action(detail=False, methods=['post'], throttle_classes=[BurstRateThrottle])
    def add_to_wishlist(self, request):
        profile = self.get_object()
        product_id = request.data.get('product_id')
        try:
            product = get_object_or_404(Product, id=product_id)
            if profile.wishlist.filter(id=product.id).exists():
                return Response({"detail": "Product already in wishlist"}, status=status.HTTP_400_BAD_REQUEST)
            profile.wishlist.add(product)
            logger.info(f"Customer {request.user.username} added {product.name} to wishlist")
            cache.delete(f"profile_{request.user.id}")
            return Response({"detail": "Product added to wishlist"}, status=status.HTTP_201_CREATED)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['delete'])
    def remove_from_wishlist(self, request):
        profile = self.get_object()
        product_id = request.data.get('product_id')
        try:
            product = get_object_or_404(Product, id=product_id)
            profile.wishlist.remove(product)
            logger.info(f"Customer {request.user.username} removed {product.name} from wishlist")
            cache.delete(f"profile_{request.user.id}")
            return Response({"detail": "Product removed from wishlist"}, status=status.HTTP_204_NO_CONTENT)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], throttle_classes=[BurstRateThrottle])
    def follow_store(self, request):
        profile = self.get_object()
        vendor_id = request.data.get('vendor_id')
        try:
            vendor = get_object_or_404(VendorProfile, id=vendor_id)
            if profile.followed_stores.filter(id=vendor.id).exists():
                return Response({"detail": "Vendor already followed"}, status=status.HTTP_400_BAD_REQUEST)
            profile.followed_stores.add(vendor)
            logger.info(f"Customer {request.user.username} followed {vendor.store_name}")
            cache.delete(f"profile_{request.user.id}")
            return Response({"detail": "Vendor followed"}, status=status.HTTP_201_CREATED)
        except VendorProfile.DoesNotExist:
            return Response({"detail": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def unfollow_store(self, request):
        profile = self.get_object()
        vendor_id = request.data.get('vendor_id')
        try:
            vendor = get_object_or_404(VendorProfile, id=vendor_id)
            profile.followed_stores.remove(vendor)
            logger.info(f"Customer {request.user.username} unfollowed {vendor.store_name}")
            cache.delete(f"profile_{request.user.id}")
            return Response({"detail": "Vendor unfollowed"}, status=status.HTTP_204_NO_CONTENT)
        except VendorProfile.DoesNotExist:
            return Response({"detail": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def followed_stores(self, request):
        profile = self.get_object()
        paginator = PageNumberPagination()
        paginator.page_size = 10
        result_page = paginator.paginate_queryset(profile.followed_stores.all(), request)
        serializer = VendorProfileSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def wishlist_items(self, request):
        profile = self.get_object()
        paginator = PageNumberPagination()
        paginator.page_size = 10
        result_page = paginator.paginate_queryset(profile.wishlist.all(), request)
        serializer = ProductSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

class VendorProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor profile actions."""
    serializer_class = VendorProfileSerializer
    permission_classes = [IsApprovedVendor]
    queryset = VendorProfile.objects.all()

    def get_object(self):
        try:
            profile = VendorProfile.objects.get(user=self.request.user)
        except VendorProfile.DoesNotExist:
            raise Http404("Vendor profile not found for this user")
        return profile

    @action(detail=False, methods=['get', 'patch'])
    @method_decorator(cache_page(60 * 15))
    def me(self, request):
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