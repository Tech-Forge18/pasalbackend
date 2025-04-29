# orders/views.py
import logging
import sentry_sdk
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.views.decorators.cache import cache_page
from django.db import transaction
from django.core.cache import cache
from django.db.models import F
from utils.mail import send_mailersend_email
from .models import Order, ShippingAddress, OrderItem
from .serializers import OrderSerializer, ShippingAddressSerializer, OrderPagination
from account.permissions import IsCustomer, IsApprovedVendor
from products.models import Product
from products.tasks import send_low_stock_alert
from cart.models import CartItem
from rest_framework import serializers

logger = logging.getLogger('gurkha_pasal')

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomer]
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
                # Stock not deducted; waits for 'to_ship'
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
                # Now delete only the cart items that were added to the order
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

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            order = self.get_object()
            if order.status not in ['to_pay', 'to_ship']:
                return Response({"detail": "Only to_pay or to_ship orders can be cancelled."}, status=400)
            order.status = 'cancelled'
            for item in order.order_items.all():
                if item.status == 'to_pay':
                    # No stock to restore
                    item.status = 'cancelled'
                    item.save()
                else:
                    # Restore stock
                    item.product.stock = F('stock') + item.quantity
                    item.product.save()
                    item.status = 'cancelled'
                    item.save()
            order.save()
            logger.info(f"Order {order.id} cancelled by {request.user.username}")
            cache.delete(f"orders_{request.user.id}")
            for item in order.order_items.all():
                cache.delete(f"product_{item.product.id}")

            if order.user.email:
                subject = f"Order #{order.id} Cancelled"
                message = (
                    f"Dear {order.user.username},\n\n"
                    f"Your order #{order.id} has been cancelled.\n"
                    f"Items:\n" + "\n".join(
                        [f"- {item.product.name} (Code: {item.product.code}, x{item.quantity})" for item in order.order_items.all()]
                    ) + "\n\n"
                    f"If this was a mistake, please contact support.\n\n"
                    f"Best regards,\nGurkha Pasal Team"
                )
                send_mailersend_email.delay(order.user.email, subject, message)

            return Response({"detail": "Order cancelled successfully."}, status=200)

    @action(detail=True, methods=['post'], permission_classes=[IsCustomer])
    def return_order(self, request, pk=None):
        with transaction.atomic():
            order = self.get_object()
            if order.status != 'delivered':
                return Response({"detail": "Only delivered orders can be returned."}, status=400)
            order.status = 'returned'
            for item in order.order_items.all():
                item.product.stock = F('stock') + item.quantity
                item.product.save()
                item.status = 'returned'
                item.save()
            order.save()
            logger.info(f"Order {order.id} returned by {request.user.username}")
            cache.delete(f"orders_{request.user.id}")
            for item in order.order_items.all():
                cache.delete(f"product_{item.product.id}")

            if order.user.email:
                subject = f"Order #{order.id} Return Requested"
                message = (
                    f"Dear {order.user.username},\n\n"
                    f"Your return request for order #{order.id} has been received.\n"
                    f"Items:\n" + "\n".join(
                        [f"- {item.product.name} (Code: {item.product.code}, x{item.quantity})" for item in order.order_items.all()]
                    ) + "\n\n"
                    f"We’ll process your return soon.\n\n"
                    f"Best regards,\nGurkha Pasal Team"
                )
                send_mailersend_email.delay(order.user.email, subject, message)

            return Response({"detail": "Return request submitted."}, status=200)

    @action(detail=True, methods=['post'], permission_classes=[IsApprovedVendor])
    def refund_order(self, request, pk=None):
        with transaction.atomic():
            order = self.get_object()
            if order.status != 'returned':
                return Response({"detail": "Only returned orders can be refunded."}, status=400)
            vendor_items = order.order_items.filter(product__vendor=request.user)
            if not vendor_items.exists():
                return Response({"detail": "Order does not contain your products."}, status=400)
            for item in vendor_items:
                item.status = 'refunded'
                item.save()
            if order.order_items.exclude(status='refunded').count() == 0:
                order.status = 'refunded'
                order.save()
            logger.info(f"Order {order.id} refunded by vendor {request.user.username}")
            cache.delete(f"orders_{order.user.id}")
            for item in vendor_items:
                cache.delete(f"product_{item.product.id}")

            if order.user.email:
                subject = f"Order #{order.id} Refunded"
                message = (
                    f"Dear {order.user.username},\n\n"
                    f"Your order #{order.id} has been refunded.\n"
                    f"Items:\n" + "\n".join(
                        [f"- {item.product.name} (Code: {item.product.code}, x{item.quantity})" for item in vendor_items]
                    ) + "\n\n"
                    f"Best regards,\nGurkha Pasal Team"
                )
                send_mailersend_email.delay(order.user.email, subject, message)

            return Response({"detail": "Order refunded successfully."}, status=200)

    @action(detail=False, methods=['get', 'post'])
    @cache_page(60 * 15)
    def shipping_addresses(self, request):
        user = request.user
        cache_key = f"shipping_addresses_{user.id}"
        if request.method == 'POST':
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
        addresses = cache.get(cache_key)
        if addresses is None:
            addresses = user.shipping_addresses.all()
            serialized = ShippingAddressSerializer(addresses, many=True).data
            cache.set(cache_key, serialized, 60 * 15)
            return Response(serialized)
        return Response(addresses)

    @action(detail=True, methods=['patch'], permission_classes=[IsApprovedVendor])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = dict(STATUS_CHOICES)

        if new_status not in valid_statuses:
            return Response({"detail": "Invalid order status."}, status=400)

        vendor_items = order.order_items.filter(product__vendor=request.user)
        if not vendor_items.exists():
            return Response({"detail": "Order does not contain your products."}, status=400)

        low_stock_products = []
        for item in vendor_items:
            old_status = item.status
            if new_status == 'to_ship' and old_status == 'to_pay':
                # Deduct stock when confirming order
                product = Product.objects.select_for_update().get(id=item.product.id)
                if product.stock < item.quantity:
                    return Response({"detail": f"Insufficient stock for {product.name}"}, status=400)
                product.stock = F('stock') - item.quantity
                product.save()
                if product.is_low_stock:
                    low_stock_products.append(product)
            elif new_status == 'failed' and old_status in ['to_pay', 'to_ship']:
                # No stock restoration needed
                item.status = 'failed'
                item.save()
            item.status = new_status
            item.save()
            cache.delete(f"product_{item.product.id}")

            if order.user.email:
                if new_status == 'to_ship' and old_status == 'to_pay':
                    subject = f"Order #{order.id} Confirmed"
                    message = (
                        f"Dear {order.user.username},\n\n"
                        f"Your order #{order.id} has been confirmed and is ready to ship.\n"
                        f"Item: {item.product.name} (Code: {item.product.code}, x{item.quantity})\n"
                        f"Payment due on delivery.\n"
                        f"We’ll notify you when it’s shipped.\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(order.user.email, subject, message)
                elif new_status == 'to_receive' and old_status != 'to_receive':
                    subject = f"Order #{order.id} Shipped"
                    message = (
                        f"Dear {order.user.username},\n\n"
                        f"Good news! Your order #{order.id} has been shipped.\n"
                        f"Item: {item.product.name} (Code: {item.product.code}, x{item.quantity})\n"
                        f"Shipping Address: {order.shipping_address.full_address}\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(order.user.email, subject, message)
                elif new_status == 'delivered' and old_status != 'delivered':
                    subject = f"Order #{order.id} Delivered"
                    message = (
                        f"Dear {order.user.username},\n\n"
                        f"Your order #{order.id} has been delivered!\n"
                        f"Item: {item.product.name} (Code: {item.product.code}, x{item.quantity})\n"
                        f"We hope you enjoy your purchase.\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(order.user.email, subject, message)
                elif new_status == 'completed' and old_status != 'completed':
                    subject = f"Order #{order.id} Completed"
                    message = (
                        f"Dear {order.user.username},\n\n"
                        f"Your order #{order.id} is now completed.\n"
                        f"Item: {item.product.name} (Code: {item.product.code}, x{item.quantity})\n"
                        f"Thank you for shopping with us!\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(order.user.email, subject, message)
                elif new_status == 'failed' and old_status != 'failed':
                    subject = f"Order #{order.id} Failed"
                    message = (
                        f"Dear {order.user.username},\n\n"
                        f"Unfortunately, your order #{order.id} could not be processed.\n"
                        f"Item: {item.product.name} (Code: {item.product.code}, x{item.quantity})\n"
                        f"Please contact support for assistance.\n\n"
                        f"Best regards,\nGurkha Pasal Team"
                    )
                    send_mailersend_email.delay(order.user.email, subject, message)

        if order.order_items.exclude(status=new_status).count() == 0:
            order.status = new_status
            order.save()

        for product in set(low_stock_products):
            send_low_stock_alert.delay(product.vendor.id, [product.id])

        logger.info(f"Vendor {request.user.username} updated order {order.id} items to {new_status}")
        cache.delete(f"orders_{order.user.id}")
        return Response({"detail": "Order status updated successfully."}, status=200)