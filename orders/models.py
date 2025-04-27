# orders/models.py
from django.db import models
from django.core.validators import MinValueValidator
from account.models import User
from products.models import Product
from .constants import STATUS_CHOICES

class ShippingAddress(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shipping_addresses',
        limit_choices_to={'role': 'customer'}
    )
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Nepal")
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_default:
            ShippingAddress.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.address_line1}"

    @property
    def full_address(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.postal_code, self.country]
        return ", ".join(part for part in parts if part)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    shipping_address = models.ForeignKey(
        ShippingAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_pay')

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} ({self.status})"

    def calculate_total(self):
        total = sum(item.price_at_time * item.quantity for item in self.order_items.all())
        self.total_amount = total
        self.save()

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)
    selected_color = models.CharField(max_length=50, blank=True, null=True)
    selected_size = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_pay')

    def save(self, *args, **kwargs):
        if not self.price_at_time and self.product:
            self.price_at_time = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} (x{self.quantity}) in Order #{self.order.id}"

    class Meta:
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]