import logging
import sentry_sdk
from rest_framework import viewsets, permissions, status
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.core.cache import cache
from ..models import Order, OrderItem
from ..serializers import OrderSerializer, OrderPagination
from account.permissions import IsCustomer
from products.models import Product
from cart.models import CartItem
from utils.mail import send_mailersend_email

logger = logging.getLogger('gurkha_pasal')

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny] if settings.DEBUG else [IsCustomer]
    pagination_class = OrderPagination

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related('user', 'shipping_address').prefetch_related('order_items__product')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
        
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            with sentry_sdk.start_transaction(op="order.create", name="Create Order"):
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                order_items_data = serializer.validated_data.get('order_items', [])
                order = serializer.save(user=self.request.user, status='to_pay')
                total_amount = 0
                for item_data in order_items_data:
                    product = item_data['product']
                    quantity = item_data['quantity']
                    total_amount += product.price * quantity
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price_at_time=product.price,
                        selected_color=item_data.get('selected_color'),
                        selected_size=item_data.get('selected_size'),
                        status='to_pay'
                    )
                order.total_amount = total_amount
                order.save()
                ordered_product_ids = [item_data['product'].id for item_data in order_items_data]
                CartItem.objects.filter(user=request.user, product_id__in=ordered_product_ids).delete()
                response_data = OrderSerializer(order, context={'request': request}).data
                logger.info(f"Order {order.id} created by {request.user.username} with status 'to_pay'")
                sentry_sdk.capture_message(
                    f"Order {order.id} created: {order.total_amount} NPR, Status: to_pay, Shipping: {order.shipping_address.full_address}",
                    level="info"
                )
                cache.delete(f"orders_{request.user.id}")
                for item in order.order_items.all():
                    cache.delete(f"product_{item.product.id}")

                if request.user.email:
                    customer_subject = f"Order Placed - Order #{order.id}"
                    customer_message = (
                        f"Dear {request.user.username},\n\n"
                        f"Your order #{order.id} has been placed.\n"
                        f"Total Amount: NPR {order.total_amount}\n"
                        f"Items:\n" + "\n".join(
                            [f"- {item.product.name} (Code: {item.product.code}, x{item.quantity})" for item in order.order_items.all()]
                        ) + "\n\n"
                        f"Shipping Address: {order.shipping_address.full_address}\n\n"
                        f"Payment is due on delivery (Cash on Delivery).\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(request.user.email, customer_subject, customer_message)

                vendor_items = {}
                for item in order.order_items.all():
                    vendor = item.product.vendor
                    if vendor.email:
                        if vendor not in vendor_items:
                            vendor_items[vendor] = []
                        vendor_items[vendor].append(item)
                
                for vendor, items in vendor_items.items():
                    vendor_subject = f"New Order Notification - Order #{order.id}"
                    vendor_message = (
                        f"Dear {vendor.username},\n\n"
                        f"A new order #{order.id} includes your products.\n" +
                        "\n".join([f"- {item.product.name} (Code: {item.product.code}, x{item.quantity})" for item in items]) +
                        f"\nCustomer: {request.user.username}\n"
                        f"Total Order Amount: NPR {order.total_amount}\n\n"
                        f"Await confirmation before fulfillment; payment due on delivery.\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(vendor.email, vendor_subject, vendor_message)

                return Response(response_data, status=201)