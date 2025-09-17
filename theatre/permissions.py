from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrReadOnly(BasePermission):
    """
    Custom permission to allow read-only access for any user but restrict modifications
    to admin users.

    This permission class ensures that safe methods (e.g., GET, OPTIONS, HEAD) are
    accessible by all users, while write permissions are restricted to authenticated
    admin users only.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
