from django.db import models
from django.core.validators import RegexValidator
from account.models import User

class Profile(models.Model):
    """Customer profile details."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile',
                                limit_choices_to={'role': 'customer'})
    bio = models.TextField(max_length=500, blank=True, null=True)
    phone_validator = RegexValidator(regex=r'^\+?977?\d{9,15}$', message="Phone number must be in format: '+977123456789'.")
    phone_number = models.CharField(max_length=15, blank=True, null=True, validators=[phone_validator])
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    wishlist = models.ManyToManyField('products.Product', blank=True, related_name='wishlisted_by')

    def __str__(self):
        return f"{self.user.username}'s Profile"

class VendorProfile(models.Model):
    """Vendor profile details."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile',
                                limit_choices_to={'role': 'vendor'})
    store_name = models.CharField(max_length=100)
    store_logo = models.ImageField(upload_to='store_logos/', blank=True, null=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Nepal")
    contact_email = models.EmailField()

    def __str__(self):
        return f"{self.store_name} ({self.user.username})"

    @property
    def full_address(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.postal_code, self.country]
        return ", ".join(part for part in parts if part)