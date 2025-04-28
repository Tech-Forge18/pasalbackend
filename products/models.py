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
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['parent_category']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['vendor', 'name', 'parent_category'], name='unique_category_name_per_vendor')
        ]

class ProductManager(models.Manager):
    def low_stock(self, vendor):
        return self.filter(vendor=vendor, stock__lte=F('stock_threshold'))

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    brand = models.CharField(max_length=100, null=True, blank=True)
    specification = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.IntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    rating = models.FloatField(default=0.0)
    code = models.CharField(max_length=50, null=True, blank=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
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
        return f"{self.name} ({self.code or 'No Code'})"

    def generate_unique_slug(self):
        base_slug = slugify(self.name)
        slug = f"{base_slug}-{self.code.lower() if self.code else self.id or 'temp'}"
        original_slug = slug
        counter = 1
        while Product.objects.filter(slug=slug).exclude(id=self.id).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"PROD-{self.id or 'temp'}"
        if not self.slug:
            self.slug = self.generate_unique_slug()
        if self.stock < 0:
            raise ValueError("Stock cannot be negative")
        super().save(*args, **kwargs)
        if 'temp' in (self.code or '') or 'temp' in (self.slug or ''):
            self.code = f"PROD-{self.id}"
            self.slug = self.generate_unique_slug()
            super().save(update_fields=['code', 'slug'])

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
            models.UniqueConstraint(
                fields=['vendor', 'code'],
                name='unique_vendor_code',
                condition=models.Q(code__isnull=False)
            ),
        ]

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='product_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        indexes = [
            models.Index(fields=['product']),
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