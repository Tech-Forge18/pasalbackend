from rest_framework import permissions

class IsCustomer(permissions.BasePermission):
    """Allows access only to users with 'customer' role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'

class IsApprovedVendor(permissions.BasePermission):
    """Allows access only to approved vendors."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'vendor' and request.user.is_approved

class IsAdmin(permissions.BasePermission):
    """Allows access only to admin users."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'