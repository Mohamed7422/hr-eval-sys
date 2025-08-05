from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from evaluation_app.models import Objective, Employee
from evaluation_app.serializers.objective_serializer import ObjectiveSerializer
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, IsSelfOrAdminHR

class ObjectiveViewSet(viewsets.ModelViewSet):
    queryset         = Objective.objects.select_related("evaluation__employee")
    serializer_class = ObjectiveSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        role   = self.request.user.role
        action = self.action

        # ─── LIST / RETRIEVE ───────────────────────────────
        if action in ("list", "retrieve"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
            return [IsSelfOrAdminHR()]

        # ─── CREATE / UPDATE / PARTIAL_UPDATE ──────────────
        if action in ("create", "update", "partial_update"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            return [(IsHOD|IsLineManager)()]

        # ─── DESTROY ───────────────────────────────────────
        if action == "destroy":
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            self.permission_denied(self.request, message="You cannot delete objectives.")

        return super().get_permissions()

    def get_queryset(self):
        qs   = super().get_queryset()
        user = self.request.user

        if user.role in ("ADMIN", "HR"):
            return qs
        if user.role in ("HOD", "LM"):
            # only objectives whose evaluation’s employee they manage
            return qs.filter(evaluation__employee__departments__manager=user).distinct()
        # regular employee only sees their own objectives
        return qs.filter(evaluation__employee__user=user)
