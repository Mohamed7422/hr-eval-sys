from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsHR(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "HR"

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "ADMIN"

class IsHOD(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "HOD"

class IsLineManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "LM"
    

class IsAdminOrHR(BasePermission):
    """
    Grants permission when the user is ADMIN **or** HR.
    """
    def has_permission(self, request, view):
        return request.user.role in ("ADMIN", "HR")
    


class ReadOnlyOrAdminHR(BasePermission):
    """
    - SAFE methods (GET / HEAD / OPTIONS) → everybody.
    - Mutating methods (POST / PUT / PATCH / DELETE) → Admin or HR only.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in ("ADMIN", "HR")




class IsSelfOrAdminHR(BasePermission):
    """
    Employees can view their own profile.
    HR & Admin can view everyone.
    """
    def has_permission(self, request, view):
        #Allow view-level access for authenticated users
        # The actual filtering happens in has_object_permission
        return request.user and request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.user.role in ("ADMIN", "HR"):
            return True
        return obj.user_id == request.user.user_id