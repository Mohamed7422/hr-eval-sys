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
        
        action = self.action
        role = getattr(self.request.user, 'role', None)
         
        # ─── SELF_EVALUATE ───────────────────────────────────── 
        if action == "self_evaluate": 
            return [IsAuthenticated()]
        
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
            #checks happened in destry method down.
            return [IsAuthenticated()]
        
          

        # Fallback (shouldn’t get here)-Just in case
        return super().get_permissions()
        
    # ---- queryset filtered by role ---------------------------
    
    def get_queryset(self):
        qs = (Evaluation.objects
              .select_related("employee__user","reviewer")
              .prefetch_related("objective_set", "competency_set")
              ) 
        user = self.request.user
        
        if self.action == "self_evaluate":
            qs = qs.filter(status=EvalStatus.SELF_EVAL)
        elif self.action in ("destroy", "update", "partial_update"): 
            pass   
        else:
            qs = qs.exclude(status=EvalStatus.SELF_EVAL)
       
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
        user = request.user

        if instance.status == EvalStatus.SELF_EVAL:
            emp = getattr(user, "employee_profile", None)
            if emp and instance.employee == emp:
                self.perform_destroy(instance)
                return Response({
                    "message": "Evaluation deleted successfully."
                },status=status.HTTP_204_NO_CONTENT)

        if user.role not in ("ADMIN", "HR", "HOD", "LM"):
            self.permission_denied(request, message="You cannot delete evaluations.")    


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
        year = params.get("year")
        from_date = params.get("from")
        to_date = params.get("to")
        
        qs = self.get_queryset()

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
        

        if year: 
            try:
                year_int = int(year)
                qs = qs.filter(created_at__year=year_int)   
            except Exception:
                return Response({
                "error": "Invalid year format. Please provide a valid year (e.g., 2025)."
                }, status=status.HTTP_400_BAD_REQUEST)
             
    
           
        if from_date:
            try:
                start = datetime.fromisoformat(from_date).astimezone(timezone.utc)
                qs = qs.filter(created_at__gte=start)
            except ValueError:
                return Response({
                    "error": "Invalid 'from' date format. Use ISO format (YYYY-MM-DD)."
                }, status=status.HTTP_400_BAD_REQUEST)
    
        if to_date:
            try:
                end = datetime.fromisoformat(to_date).astimezone(timezone.utc)
                qs = qs.filter(updated_at__lte=end)
            except ValueError:
                return Response({
                    "error": "Invalid 'to' date format. Use ISO format (YYYY-MM-DD)."
                }, status=status.HTTP_400_BAD_REQUEST)

        agg = qs.aggregate(count=Count("pk"), 
                           sum=Sum(Coalesce("score", Decimal("0.00"))))
        count = agg.get("count") or 0
        total = agg.get("sum") or Decimal("0.00")
        
        # Calculate average
        if count > 0:
            average = float(total) / count
        else:
            average = 0.0
        

        return Response({
            "count": count,
            "sum": float(total),
            "average": round(average, 2)
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["post", "get"], url_path = "self-evaluate")
    def self_evaluate(self, request, *args, **kwargs):
        user = request.user
        
        if request.method == "GET":
            qs = self.get_queryset()

            employee_id = request.query_params.get("employee_id")
            if employee_id:
                if user.role not in ("ADMIN", "HR", "HOD", "LM"):
                    return Response(
                        {"error": "You don't have permission to filter by employee_id."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                qs = qs.filter(employee__employee_id=employee_id)
            else:
                # No employee_id filter - show current user's own self-evaluations
                emp = getattr(user, "employee_profile", None)
                if not emp:
                    return Response({"error": "User has no employee profile."}, status=status.HTTP_400_BAD_REQUEST)
                qs = qs.filter(employee=emp)
    
            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
       
        emp = getattr(user, "employee_profile", None)
        if not emp: 
            return Response({"error": "User has no employee profile."}, status=status.HTTP_400_BAD_REQUEST)
       
       
       
        payload = request.data or {}
        eval_type = payload.get("type", EvalType.OPTIONAL)
        period = payload.get("period")
        if not period:
            return Response({"error": "Period is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        
        instance = Evaluation.objects.create(employee=emp,
                                             type= eval_type,
                                             period=period,
                                             status=EvalStatus.SELF_EVAL,
                                             reviewer=None,)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)