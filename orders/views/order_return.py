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

class OrderReturnView:
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
                    f"We'll process your return soon.\n\n"
                    f"Best regards,\nGurkha Pasal Team"
                )
                send_mailersend_email.delay(order.user.email, subject, message)

            return Response({"detail": "Return request submitted."}, status=200)