from rest_framework import viewsets, status, filters
 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from evaluation_app.filters import ObjectiveFilter
from evaluation_app.models import Objective, EmployeePlacement
from evaluation_app.serializers.objective_serializer import ObjectiveSerializer
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager 
from django.db.models import Q 
class ObjectiveViewSet(viewsets.ModelViewSet):
    queryset         = Objective.objects.select_related("evaluation__employee")
    serializer_class = ObjectiveSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] 
    filterset_class = ObjectiveFilter 
    search_fields = ["title","evaluation_id"]
    ordering_fields = ["created_at", "updated_at", "weight"]
    def get_permissions(self):
        role   = self.request.user.role
        action = self.action

        # ─── LIST / RETRIEVE ───────────────────────────────
        if action in ("list", "retrieve"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
            return [IsAuthenticated()]

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
        qs   = Objective.objects.select_related("evaluation__employee__user")
        user = self.request.user

        if user.role in ("ADMIN", "HR"):
            return qs
        if user.role in ("HOD", "LM"):
            # only objectives whose evaluation’s employee they manage
            return qs.filter(
                evaluation__employee__employee_placements__in=EmployeePlacement.objects.filter(
                    Q(department__manager=user) | 
                    Q(sub_department__manager=user) | 
                    Q(section__manager=user) |
                    Q(sub_section__manager=user))).distinct() 
        # regular employee only sees their own objectives
        return qs.filter(evaluation__employee__user=user)


    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj =ser.save() #triggers objective post_save signal to recalculate weights
        #pull in bulk update changes done by the signal
        obj.refresh_from_db(fields=["weight","updated_at"])
        data = self.get_serializer(obj).data
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)
    

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        obj =ser.save() #triggers objective post_save signal to recalculate weights
        #pull in bulk update changes done by the signal
        obj.refresh_from_db(fields=["weight","updated_at"])
        data = self.get_serializer(obj).data
        return Response(data)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().partial_update(request, *args, **kwargs)