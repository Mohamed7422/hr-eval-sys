from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsHR(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "HR"

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "Admin"

class IsHOD(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "HOD"

class IsLineManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "LM"


class IsSelfOrAdminHR(BasePermission):
    """
    Employees can view their own profile.
    HR & Admin can view everyone.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role in ("ADMIN", "HR"):
            return True
        return obj.user_id == request.user.user_id