from rest_framework import viewsets, status,mixins, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from rest_framework.response import Response
from evaluation_app.serializers.evaluation_serilizer import (
    EvaluationSerializer, ObjectiveSerializer
)
import django_filters
from rest_framework.permissions import IsAuthenticated

from evaluation_app.models import (
    Evaluation, Employee, Objective, EvalStatus, EvalType
)
from evaluation_app.permissions import(
    IsAdmin, IsHR, IsHOD, IsLineManager, IsSelfOrAdminHR
)

class EvaluationFilter(django_filters.FilterSet):
    employee_id = django_filters.UUIDFilter(field_name="employee__employee_id")

    class Meta:
        model = Evaluation
        fields = ["employee", "employee_id"]  # both work

class EvaluationViewSet(viewsets.ModelViewSet):
    """
    Permissions
    -----------
    • ADMIN / HR      → full CRUD.  
    • HOD / LM        → may create evaluations **only** for employees
                        they manage; may update those evaluations.  
    • Employee        → read-only access to own evaluations.  
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    permission_classes = [IsAuthenticated]  #default fallback
    serializer_class = EvaluationSerializer
   
    filterset_class = EvaluationFilter
    

    #----dynamic permissions----
    def get_permissions(self):
        role = self.request.user.role
        action = self.action

         # ─── LIST / RETRIEVE ─────────────────────────────────────
        if action in ("list", "retrieve"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
            return [IsSelfOrAdminHR()]
        
        # ─── CREATE / UPDATE / PARTIAL_UPDATE ───────────────────
        if action in ("create", "update", "partial_update"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            return [(IsHOD|IsLineManager)()]
        
        # ─── DESTROY ────────────────────────────────────────────
        if action == "destroy":
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            self.permission_denied(self.request, message="You cannot delete evaluations.")

        # Fallback (shouldn’t get here)-Just in case
        return super().get_permissions()
        
    # ---- queryset filtered by role ---------------------------
    
    def get_queryset(self):
        qs = (Evaluation.objects
              .select_related("employee__user","reviewer")
              .prefetch_related("objective_set", "competency_set")
              ) 
        user = self.request.user
        if user.role in ("ADMIN", "HR"):
            return qs
        if user.role in ("HOD", "LM"):
            return qs.filter(employee__departments__manager=user).distinct()
        return qs.filter(employee__user=user)
    # ----------------------------------------------------------

    # ---- extra validation for LM / HOD -----------------------
    def perform_create(self, serializer):
        print(">> perform_create by", self.request.user, self.request.user.role)
        print(">> incoming validated data:", serializer.validated_data)
        user = self.request.user
        employee_id = self.request.data.get("employee_id")

        # LM & HOD may only create evaluations for employees they manage
        if user.role in ("HOD", "LM"):
           managed = Employee.objects.filter(
               departments__manager=user,employee_id=employee_id
           ).exists()
           if not managed:
               return Response(
                   {"detail": "You can only create evaluations for employees you manage."},
                   status=status.HTTP_403_FORBIDDEN
               )
        # Admin & HR may create evaluations for any employee
        serializer.save()

   
    # ----------------------------------------------------------       
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            "message": "Evaluation deleted successfully."
        },status=status.HTTP_204_NO_CONTENT)