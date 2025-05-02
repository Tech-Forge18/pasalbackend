import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.core.cache import cache
from ..models import Order
from utils.mail import send_mailersend_email
from account.permissions import IsVendor

logger = logging.getLogger('gurkha_pasal')

class OrderRefundView:
    @action(detail=True, methods=['post'], permission_classes=[IsVendor])
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