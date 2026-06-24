# evaluation_app/views/activity_log_viewset.py
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from evaluation_app.models import ActivityLog
from django.db.models import Q
from evaluation_app.serializers.activity_log import ActivityLogSerializer

class ActivityLogViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["evaluation", "evaluation_id"]   # also allow ?evaluation_id=
    ordering = ["created_at"]

    def get_queryset(self):
        qs = ActivityLog.objects.select_related("evaluation", "actor")
        u = self.request.user
        # ADMIN/HR: see all
        if u.role in ("ADMIN", "HR"):
            return qs
        # HOD/LM: restrict to evaluations they manage (reuse your managed filter logic)
        if u.role in ("HOD", "LM"):
            return qs.filter(
                Q(evaluation__employee__employee_placements__department__manager=u) |
                Q(evaluation__employee__employee_placements__sub_department__manager=u) |
                Q(evaluation__employee__employee_placements__section__manager=u) |
                Q(evaluation__employee__employee_placements__sub_section__manager=u)
            ).distinct()
        # Employee: only logs for their own evaluations
        return qs.filter(evaluation__employee__user=u)

    def perform_create(self, serializer):
        # enforce that the actor defaults to request.user
        serializer.save()
 