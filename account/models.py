# account/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError

class UserManager(BaseUserManager):
    """Custom manager for User model."""
    def create_user(self, username, password=None, **extra_fields):
        """Create and save a regular user."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', 'customer')  # Default role

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        """Create and save a superuser with role='admin'."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # Force role to 'admin'
        extra_fields.setdefault('is_approved', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('role') != 'admin':
            raise ValueError('Superuser must have role="admin".')

        return self.create_user(username, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    is_approved = models.BooleanField(default=False, help_text="Approval status for vendors.")

    # Use custom manager
    objects = UserManager()

    def clean(self):
        """Validate role consistency."""
        if self.role == 'vendor' and self.is_superuser:
            raise ValidationError("A vendor cannot be a superuser.")
        if self.role == 'customer' and (self.is_staff or self.is_superuser):
            raise ValidationError("A customer cannot have staff or superuser privileges.")

    def save(self, *args, **kwargs):
        """Set defaults only on creation, respect manager logic."""
        if not self.pk:  # Only on creation
            if self.is_superuser or self.is_staff:
                self.role = 'admin'
                self.is_approved = True
            elif self.role == 'vendor':
                self.is_staff = False
                self.is_superuser = False
            elif self.role == 'customer':
                self.is_staff = False
                self.is_superuser = False
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username