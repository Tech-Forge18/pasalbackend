# cart/models.py
from django.db import models
from django.core.validators import MinValueValidator

class CartItem(models.Model):
    user = models.ForeignKey('account.User', on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    selected_color = models.CharField(max_length=100, blank=True, null=True)
    selected_size = models.CharField(max_length=100, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product', 'selected_color', 'selected_size']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} (x{self.quantity})"
