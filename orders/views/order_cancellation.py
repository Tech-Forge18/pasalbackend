import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from ..models import Order
from utils.mail import send_mailersend_email
from account.permissions import IsCustomer

logger = logging.getLogger('gurkha_pasal')

class OrderCancellationView:
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            order = self.get_object()
            if order.status not in ['to_pay', 'to_ship']:
                return Response({"detail": "Only to_pay or to_ship orders can be cancelled."}, status=400)
            order.status = 'cancelled'
            for item in order.order_items.all():
                if item.status == 'to_pay':
                    item.status = 'cancelled'
                    item.save()
                else:
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