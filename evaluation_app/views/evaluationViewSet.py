from rest_framework import viewsets, status,mixins
from django.db.models import Prefetch
from rest_framework.response import Response
from evaluation_app.serializers.evaluation_serilizer import (
    EvaluationSerializer, ObjectiveSerializer
)
from rest_framework.permissions import IsAuthenticated

from evaluation_app.models import (
    Evaluation, Employee, Objective, EvalStatus, EvalType
)
from evaluation_app.permissions import(
    IsAdmin, IsHR, IsHOD, IsLineManager, IsSelfOrAdminHR
)

class EvaluationViewSet(viewsets.ModelViewSet):
    """
    Permissions
    -----------
    • ADMIN / HR      → full CRUD.  
    • HOD / LM        → may create evaluations **only** for employees
                        they manage; may update those evaluations.  
    • Employee        → read-only access to own evaluations.  
    """
    permission_classes = [IsAuthenticated]  #default fallback
    serializer_class = EvaluationSerializer
    
    #----dynamic permissions----
    def get_permissions(self):
        
        if self.action in ("list", "retrieve"):
            #reading
            if self.request.user.role in ("ADMIN", "HR"):
                return [(IsAdmin | IsHR)()]  
            if self.request.user.role in ("HOD", "LM"):
                return [(IsHOD | IsLineManager)()]
            return [IsSelfOrAdminHR()]
        #creating, updating, deleting
        if self.request.user.role in ("ADMIN", "HR"):
            return [(IsAdmin | IsHR)()]
        
        return [(IsHOD | IsLineManager)()] # LM & HOD restricted further in perform_create
    # ----------------------------------------------------------
    # ---- queryset filtered by role ---------------------------
    
    def get_queryset(self):
        qs = (Evaluation.objects.select_related("employee__user","reviewer")
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


        if user.role in ("HOD", "LM"):
           managed = Employee.objects.filter(
               departments__manager=user,employee_id=employee_id
           ).exists()
           if not managed:
               return Response(
                   {"detail": "You can only create evaluations for employees you manage."},
                   status=status.HTTP_403_FORBIDDEN
               )
    
           serializer.save()

   
    # ----------------------------------------------------------       