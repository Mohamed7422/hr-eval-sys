from rest_framework.permissions import IsAuthenticated
from evaluation_app.permissions import ReadOnlyOrAdminHR
from django.db.models import Q
from django.core.exceptions import FieldDoesNotExist
class ReadOnlyAuthFullAdminHRMixin:

    manager_lookups = ["manager"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [ReadOnlyOrAdminHR()]
    

    def _managet_query(self, user):
        q = Q()
        for lookup in getattr(self, "manager_lookups", ["manager"]):
            try:
                q |= Q(**{lookup: user})
            except FieldDoesNotExist:
                # Silently skip invalid lookups (e.g., during development)
                pass
        return q
    def get_queryset(self):
        qs = super().get_queryset()
        u  = self.request.user
        if u.role in ("Admin", "HR", "ADMIN"):
            return qs
        if u.role in ("HOD", "LM"):
            return qs.filter(self._managet_query(u)).distinct()

        return qs.none()