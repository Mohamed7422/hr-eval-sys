# evaluation_app/views/competency_viewset.py

from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from evaluation_app.filters import CompetencyFilter
from django_filters.rest_framework import DjangoFilterBackend
from evaluation_app.models import Competency
from evaluation_app.serializers.competency_serializer import CompetencySerializer
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, IsSelfOrAdminHR

class CompetencyViewSet(viewsets.ModelViewSet):
    """
    • ADMIN/HR → full CRUD on all competencies
    • HOD/LM  → can list/retrieve competencies only for employees they manage;
                 can create/update/delete likewise
    • Employee → read-only on their own competencies
    """
    serializer_class = CompetencySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CompetencyFilter
    search_fields = ["name", "category"]
    ordering_fields = ["created_at", "updated_at"]

    def get_permissions(self):
        role = self.request.user.role

        # LIST & RETRIEVE
        if self.action in ("list", "retrieve"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
            return [IsSelfOrAdminHR()]

        # CREATE / UPDATE / DELETE
        if role in ("ADMIN", "HR"):
            return [(IsAdmin|IsHR)()]

        if role in ("HOD", "LM"):
            return [(IsHOD|IsLineManager)()]

        # Everyone else forbidden
        self.permission_denied(self.request)

    def get_queryset(self):
        qs = Competency.objects.select_related("evaluation__employee__user")
        user = self.request.user

        if user.role in ("ADMIN", "HR"):
            return qs

        if user.role in ("HOD", "LM"):
            # only competencies for employees they manage
            return qs.filter(evaluation__employee__departments__manager=user).distinct()

        # regular employee only sees own
        return qs.filter(evaluation__employee__user=user)
