# account/permissions.py
from rest_framework import permissions

class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return True  # Allow all permissions
       # return request.user.is_authenticated and request.user.role == 'customer'

class IsApprovedVendor(permissions.BasePermission):
    def has_permission(self, request, view):

        return True  # Allow all permissions
        #return request.user.is_authenticated and request.user.role == 'vendor'

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):

        
        return True  # Allow all permissions
        #return request.user.is_authenticated and request.user.role == 'admin'