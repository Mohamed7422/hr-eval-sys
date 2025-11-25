from rest_framework import viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import  Q, Sum, Count
from rest_framework.response import Response
from evaluation_app.serializers.evaluation_serilizer import (
    EvaluationSerializer
)
from decimal import Decimal
from django.db.models.functions import Coalesce
from datetime import datetime, timezone
from rest_framework.decorators import action
import django_filters
from rest_framework.permissions import IsAuthenticated

from evaluation_app.models import (
    Evaluation, Employee, EmployeePlacement, EvalStatus, EvalType  
)
from evaluation_app.permissions import(
    IsAdmin, IsHR, IsHOD, IsLineManager 
)

from evaluation_app.utils import LabelChoiceField

class EvaluationFilter(django_filters.FilterSet):
    employee_id = django_filters.UUIDFilter(field_name="employee__employee_id")
    user_id = django_filters.UUIDFilter(field_name="employee__user__user_id")

    class Meta:
        model = Evaluation
        fields = ["employee", "employee_id" , "user_id"]  # both work

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
            return [IsAuthenticated()]
        
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
            return qs.filter(
                employee__employee_placements__in=EmployeePlacement.objects.filter(
                    Q(department__manager=user) |
                    Q(sub_department__manager=user) |
                    Q(section__manager=user) |
                    Q(sub_section__manager=user)
                )
            ).distinct()
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
               employee_id=employee_id,
               employee_placements__in=EmployeePlacement.objects.filter(
                   Q(department__manager=user) |
                   Q(sub_department__manager=user) |
                   Q(section__manager=user) |
                   Q(sub_section__manager=user)
               )
           ).exists()
           if not managed:
               self.permission_denied(
                   self.request,
                   message="You can only create evaluations for employees you manage."
               )

        # Admin & HR may create evaluations for any employee
        instance = serializer.save()
        return instance      
      
    # ----------------------------------------------------------       

    def perform_update(self, serializer):
        instance = serializer.save()
        return instance

        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            "message": "Evaluation deleted successfully."
        },status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=["get"],
            url_path="summary",
            permission_classes=[IsAuthenticated])
    def summary(self, request):
        params = request.query_params
        emp_id = params.get("employee_id")
        type_filter = params.get("type")
        status_filter = params.get("status")
        start = datetime.fromisoformat(params.get("from")).astimezone(timezone.utc)
        end = datetime.fromisoformat(params.get("to")).astimezone(timezone.utc)
        
        qs = self.get_queryset()
        print(f"qs: {emp_id} type: {type_filter} status: {status_filter} start: {start} end: {end}") 
        if emp_id:
            qs = qs.filter(employee__employee_id=emp_id)
        # Normalize and validate type using LabelChoiceField supporting labels and values
        if type_filter:
            type_field = LabelChoiceField(choices=EvalType.choices, required=False)
            try:
                type_value = type_field.to_internal_value(type_filter)
            except Exception:
                valid_types = [choice[0] for choice in EvalType.choices]
                valid_type_labels = [choice[1] for choice in EvalType.choices]
                return Response({
                    "error": "Invalid type.",
                    "allowed_values": valid_types,
                    "allowed_labels": valid_type_labels,
                }, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(type=type_value)
        else:
            qs = qs.filter(type=EvalType.ANNUAL)

        # Normalize and validate status using LabelChoiceField supporting labels and values
        if status_filter:
            status_field = LabelChoiceField(choices=EvalStatus.choices, required=False)
            try:
                status_value = status_field.to_internal_value(status_filter)
            except Exception:
                valid_statuses = [choice[0] for choice in EvalStatus.choices]
                valid_status_labels = [choice[1] for choice in EvalStatus.choices]
                return Response({
                    "error": "Invalid status.",
                    "allowed_values": valid_statuses,
                    "allowed_labels": valid_status_labels,
                }, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(status=status_value)
        else:
            qs = qs.filter(status=EvalStatus.COMPLETED)

        if start:
            qs = qs.filter(created_at__gte=start)
        if end:
            qs = qs.filter(updated_at__lte=end)

        agg = qs.aggregate(count=Count("pk"), 
                           sum=Sum(Coalesce("score", Decimal("0.00"))))
        total = agg.get("sum") or Decimal("0.00")
        print(f"agg: {agg}")
        try:
            total = float(total)
        except Exception:
            pass

        return Response({
            "count": agg.get("count") or 0,
            "sum": total
        }, status=status.HTTP_200_OK)
