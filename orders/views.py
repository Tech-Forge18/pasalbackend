# orders/views.py
import logging
import sentry_sdk
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.views.decorators.cache import cache_page
from django.db import transaction
from utils.mail import send_mailersend_email
from .models import Order, ShippingAddress, OrderItem
from .serializers import OrderSerializer, ShippingAddressSerializer, OrderPagination
from account.permissions import IsCustomer, IsApprovedVendor
from products.models import Product
from products.tasks import send_low_stock_alert
from cart.models import CartItem

logger = logging.getLogger('gurkha_pasal')

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomer]
    pagination_class = OrderPagination

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related('user', 'shipping_address').prefetch_related('order_items__product')

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            with sentry_sdk.start_transaction(op="order.create", name="Create Order"):
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                cart_items_data = serializer.validated_data.get('order_items', [])
                low_stock_products = []
                for item_data in cart_items_data:
                    product = item_data['product']
                    quantity = item_data['quantity']
                    product = Product.objects.select_related('vendor').get(id=product.id)
                    if product.stock < quantity:
                        raise serializers.ValidationError(f"Not enough stock for {product.name}")
                    product.stock -= quantity
                    product.save()
                    if product.is_low_stock:
                        low_stock_products.append(product)
                order = serializer.save()
                CartItem.objects.filter(user=request.user).delete()
                order.refresh_from_db()
                response_data = OrderSerializer(order, context={'request': request}).data
                logger.info(f"Order {order.id} created by {request.user.username} for {order.total_amount}")
                sentry_sdk.capture_message(
                    f"Order {order.id} created: {order.total_amount} NPR, Shipping: {order.shipping_address.full_address}",
                    level="info"
                )

                # Async email to customer (Order Placed)
                if request.user.email:
                    customer_subject = f"Order Confirmation - Order #{order.id}"
                    customer_message = (
                        f"Dear {request.user.username},\n\n"
                        f"Thank you for your order! Your order #{order.id} has been placed successfully.\n"
                        f"Total Amount: NPR {order.total_amount}\n"
                        f"Items:\n" + "\n".join(
                            [f"- {item.product.name} (x{item.quantity})" for item in order.order_items.all()]
                        ) + "\n\n"
                        f"Shipping Address: {order.shipping_address.full_address}\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(request.user.email, customer_subject, customer_message)

                # Batch vendor emails
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
                        f"A new order #{order.id} includes your products:\n" +
                        "\n".join([f"- {item.product.name} (x{item.quantity})" for item in items]) +
                        f"\nCustomer: {request.user.username}\n"
                        f"Total Order Amount: NPR {order.total_amount}\n\n"
                        f"Please prepare for fulfillment.\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(vendor.email, vendor_subject, vendor_message)

                # Low stock alerts
                for product in set(low_stock_products):
                    send_low_stock_alert.delay(product.vendor.id, [product.id])

                return Response(response_data, status=201)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            order = self.get_object()
            if order.status != 'pending':
                return Response({"detail": "Only pending orders can be cancelled."}, status=400)
            order.status = 'cancelled'
            low_stock_products = []
            for item in order.order_items.all():
                item.product.stock += item.quantity
                item.product.save()
                if item.product.is_low_stock:
                    low_stock_products.append(item.product)
                item.status = 'cancelled'
                item.save()
            order.save()
            logger.info(f"Order {order.id} cancelled by {request.user.username}")

            # Async email to customer (Order Cancelled)
            if order.user.email:
                subject = f"Order #{order.id} Cancelled"
                message = (
                    f"Dear {order.user.username},\n\n"
                    f"Your order #{order.id} has been cancelled.\n"
                    f"Items:\n" + "\n".join(
                        [f"- {item.product.name} (x{item.quantity})" for item in order.order_items.all()]
                    ) + "\n\n"
                    f"If this was a mistake, please contact support.\n\n"
                    f"Best regards,\nGurkha Pasal Team"
                )
                send_mailersend_email.delay(order.user.email, subject, message)

            # Low stock alerts
            for product in set(low_stock_products):
                send_low_stock_alert.delay(product.vendor.id, [product.id])

            return Response({"detail": "Order cancelled successfully."}, status=200)

    @action(detail=False, methods=['get', 'post'])
    @cache_page(60 * 15)
    def shipping_addresses(self, request):
        user = request.user
        if request.method == 'POST':
            serializer = ShippingAddressSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user)
            logger.info(f"Shipping address added for {user.username}")
            return Response(serializer.data, status=201)
        addresses = user.shipping_addresses.all()
        return Response(ShippingAddressSerializer(addresses, many=True).data)

    @action(detail=True, methods=['patch'], permission_classes=[IsApprovedVendor])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = dict(Order.STATUS_CHOICES)

        if new_status not in valid_statuses:
            return Response({"detail": "Invalid order status."}, status=400)

        vendor_items = order.order_items.filter(product__vendor=request.user)
        if not vendor_items.exists():
            return Response({"detail": "Order does not contain your products."}, status=400)

        for item in vendor_items:
            old_status = item.status
            item.status = new_status
            item.save()

            # Async email to customer on status change
            if order.user.email:
                if new_status == 'shipped' and old_status != 'shipped':
                    subject = f"Order #{order.id} Shipped"
                    message = (
                        f"Dear {order.user.username},\n\n"
                        f"Good news! Your order #{order.id} has been shipped.\n"
                        f"Item: {item.product.name} (x{item.quantity})\n"
                        f"Shipping Address: {order.shipping_address.full_address}\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(order.user.email, subject, message)
                elif new_status == 'delivered' and old_status != 'delivered':
                    subject = f"Order #{order.id} Delivered"
                    message = (
                        f"Dear {order.user.username},\n\n"
                        f"Your order #{order.id} has been delivered!\n"
                        f"Item: {item.product.name} (x{item.quantity})\n"
                        f"We hope you enjoy your purchase.\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(order.user.email, subject, message)

        logger.info(f"Vendor {request.user.username} updated order {order.id} items to {new_status}")
        return Response({"detail": "Order status updated successfully."}, status=200)