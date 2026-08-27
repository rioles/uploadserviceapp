from rest_framework.permissions import BasePermission


def require_role(role: str):
    class _RolePermission(BasePermission):
        def has_permission(self, request, view):
            return (
                hasattr(request.user, "has_role")
                and request.user.has_role(role)
            )

    _RolePermission.__name__ = f"HasRole_{role}"
    return _RolePermission
