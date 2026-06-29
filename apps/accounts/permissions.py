from rest_framework.permissions import BasePermission
from .models import Users


class IsAdminRole(BasePermission):
    """request.user là Accounts (từ JWTAccountAuthentication); kiểm tra role qua Users."""
    message = "Bạn không có quyền truy cập tài nguyên này."

    def has_permission(self, request, view):
        account = request.user
        if not account or not account.is_authenticated:
            return False
        try:
            return account.users.role == 'ADMIN'
        except Users.DoesNotExist:
            return False