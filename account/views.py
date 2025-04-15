import logging
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import User
from .serializers import UserSerializer
from .permissions import IsCustomer, IsApprovedVendor, IsAdmin
from orders.models import Order
from orders.serializers import OrderSerializer

logger = logging.getLogger('gurkha_pasal')

class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for customer user management."""
    serializer_class = UserSerializer
    permission_classes = [IsCustomer]
    lookup_field = 'username'
    queryset = User.objects.filter(role='customer')

    def get_object(self):
        username = self.kwargs.get(self.lookup_field)
        return get_object_or_404(self.queryset, username=username)

    def list(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    def retrieve(self, request, username=None):
        customer = self.get_object()
        if request.user != customer:
            self.check_object_permissions(request, customer)
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def orders(self, request):
        orders = request.user.orders.all()
        return Response(OrderSerializer(orders, many=True).data)

class VendorViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor user management."""
    serializer_class = UserSerializer
    permission_classes = [IsApprovedVendor]
    queryset = User.objects.filter(role='vendor')

class AdminViewSet(viewsets.ModelViewSet):
    """ViewSet for admin user management."""
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.filter(role='admin')