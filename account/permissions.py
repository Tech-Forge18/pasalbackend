from rest_framework import permissions

class IsCustomer(permissions.BasePermission):
    message = 'Only customers can access this resource.'

    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role == User.Role.CUSTOMER)

class IsApprovedVendor(permissions.BasePermission):
    message = 'Only approved vendors can access this resource.'

    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role == User.Role.VENDOR and 
                request.user.is_approved)

class IsAdmin(permissions.BasePermission):
    message = 'Only administrators can access this resource.'

    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role == User.Role.ADMIN and 
                request.user.is_staff)