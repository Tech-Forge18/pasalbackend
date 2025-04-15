from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    user = models.ForeignKey('account.User', on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='reviews/images/', blank=True, null=True)  # New field for image upload
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']  # One review per user per product

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating})"

    def clean(self):
        # Ensure user has ordered the product before reviewing
        from orders.models import Order, OrderItem
        if not Order.objects.filter(
            user=self.user,
            order_items__product=self.product,
            status__in=['processing', 'shipped', 'delivered']  # Only after order is confirmed
        ).exists():
            raise models.ValidationError("You can only review products you've ordered.")

class ReviewReply(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey('account.User', on_delete=models.CASCADE, limit_choices_to={'role': 'vendor'})
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.user.username} to {self.review}"