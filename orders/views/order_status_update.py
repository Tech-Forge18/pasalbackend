import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from ..models import Order
from products.models import Product
from products.tasks import send_low_stock_alert
from utils.mail import send_mailersend_email
from account.permissions import IsVendor

logger = logging.getLogger('gurkha_pasal')

class OrderStatusUpdateView:
    @action(detail=True, methods=['patch'], permission_classes=[IsVendor])
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
                product = Product.objects.select_for_update().get(id=item.product.id)
                if product.stock < item.quantity:
                    return Response({"detail": f"Insufficient stock for {product.name}"}, status=400)
                product.stock = F('stock') - item.quantity
                product.save()
                if product.is_low_stock:
                    low_stock_products.append(product)
            elif new_status == 'failed' and old_status in ['to_pay', 'to_ship']:
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
                        f"We'll notify you when it's shipped.\n\n"
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