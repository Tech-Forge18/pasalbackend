# reviews/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg
from .models import Review
from products.models import Product

@receiver(post_save, sender=Review)
def update_product_rating_on_review_save(sender, instance, created, **kwargs):
    """Update the product rating when a new review is added or updated."""
    product = instance.product
    reviews = product.reviews.all()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
    product.rating = round(average_rating, 1)
    product.save()

@receiver(post_delete, sender=Review)
def update_product_rating_on_review_delete(sender, instance, **kwargs):
    """Update the product rating when a review is deleted."""
    product = instance.product
    reviews = product.reviews.all()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
    product.rating = round(average_rating, 1)
    product.save()
