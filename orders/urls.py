from django.urls import path, include
from rest_framework.routers import DefaultRouter
from orders.views.order import OrderViewSet
from orders.views.order_cancellation import OrderCancellationViewSet
from orders.views.order_return import OrderReturnViewSet
from orders.views.order_refund import OrderRefundViewSet
from orders.views.order_status import OrderVendorActionViewSet
from orders.views.shipping_address import ShippingAddressViewSet

router = DefaultRouter()

# Main Order endpoints (CRUD)
router.register(r'orders', OrderViewSet, basename='orders')

# Additional Order-related endpoints
router.register(r'order-cancellations', OrderCancellationViewSet, basename='order-cancellations')
router.register(r'order-returns', OrderReturnViewSet, basename='order-returns')
router.register(r'order-refunds', OrderRefundViewSet, basename='order-refunds')
router.register(r'order-statuses', OrderVendorActionViewSet, basename='order-statuses')
router.register(r'shipping-addresses', ShippingAddressViewSet, basename='shipping-addresses')

urlpatterns = [
    path('', include(router.urls)),
]