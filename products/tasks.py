# products/tasks.py
from celery import shared_task
from .models import Product
from account.models import User
from utils.mail import send_mailersend_email

@shared_task
def send_low_stock_alert(vendor_id, product_ids):
    vendor = User.objects.get(id=vendor_id)
    products = Product.objects.filter(id__in=product_ids)
    if not products:
        return
    product_names = ", ".join(p.name for p in products)
    subject = "Low Stock Alert"
    message = (
        f"Dear {vendor.username},\n\n"
        f"The following products are below their stock threshold: {product_names}.\n"
        f"Please restock soon to avoid running out.\n\n"
        f"Best regards,\nGurkha Pasal Team"
    )
    send_mailersend_email.delay(vendor.email, subject, message)