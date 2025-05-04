from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.cache import cache
from ..models import ShippingAddress
from ..serializers import ShippingAddressSerializer
import logging

logger = logging.getLogger('gurkha_pasal')

@method_decorator(cache_page(60 * 15), name='get')
class ShippingAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cache_key = f"shipping_addresses_{user.id}"
        addresses = cache.get(cache_key)
        if addresses is None:
            addresses = user.shipping_addresses.all()
            serialized = ShippingAddressSerializer(addresses, many=True).data
            cache.set(cache_key, serialized, 60 * 15)
            return Response(serialized)
        return Response(addresses)

    def post(self, request):
        user = request.user
        cache_key = f"shipping_addresses_{user.id}"
        if user.shipping_addresses.count() >= 5:
            return Response({"detail": "Maximum 5 shipping addresses allowed."}, status=400)

        serializer = ShippingAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.shipping_addresses.exists():
            serializer.validated_data['is_default'] = True
        address = serializer.save(user=user)
        logger.info(f"Shipping address added for {user.username}")
        cache.delete(cache_key)

        if address.is_default:
            user.shipping_addresses.exclude(id=address.id).update(is_default=False)

        return Response(serializer.data, status=201)
