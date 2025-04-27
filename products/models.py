# products/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from account.models import User
from django.db.models import F

class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['vendor']),
        ]

class ProductManager(models.Manager):
    def low_stock(self, vendor):
        return self.filter(vendor=vendor, stock__lte=F('stock_threshold'))

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.IntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    image = models.ImageField(upload_to='images/')
    rating = models.FloatField(default=0.0)
    code = models.CharField(max_length=50)
    slug = models.SlugField(max_length=255, null=True, blank=True, unique=True)  # Allow null temporarily
    sold_count = models.IntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    color = models.JSONField(default=list)
    sizes = models.JSONField(default=list)
    is_exclusive_deal = models.BooleanField(default=False)
    deal_end_time = models.DateTimeField(null=True, blank=True)
    is_trending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    stock = models.PositiveIntegerField(default=0)
    stock_threshold = models.PositiveIntegerField(default=5)

    objects = ProductManager()

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{self.code.lower()}"
            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        if self.stock < 0:
            raise ValueError("Stock cannot be negative")
        super().save(*args, **kwargs)

    @property
    def is_new_arrival(self):
        return (timezone.now() - self.created_at).days < 7

    @property
    def is_low_stock(self):
        return self.stock <= self.stock_threshold

    class Meta:
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['category']),
            models.Index(fields=['slug']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['vendor', 'code'], name='unique_vendor_code'),
        ]

class Promotion(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promotions')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.discount_percent}%) by {self.vendor.username}"

    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['vendor']),
        ]