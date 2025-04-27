# orders/constants.py

# Status choices for Order and OrderItem
# to_pay: Order placed, payment pending (COD: payment left on delivery; online: awaiting payment)
# to_ship: Payment confirmed, awaiting vendor shipment
# to_receive: Shipped, awaiting delivery
# processing: Vendor preparing order (optional overlap with to_ship)
# shipped: Order dispatched (synced with to_receive)
# delivered: Order received by customer
# completed: Delivered and reviewed or return/refund window closed
# cancelled: Order voided before processing
# returned: Customer returned product
# refunded: Refund issued
# failed: Payment failed or order unprocessable
STATUS_CHOICES = (
    ('to_pay', 'To Pay'),
    ('to_ship', 'To Ship'),
    ('to_receive', 'To Receive'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('returned', 'Returned'),
    ('refunded', 'Refunded'),
    ('failed', 'Failed'),
)