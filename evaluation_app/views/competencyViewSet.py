# evaluation_app/views/competency_viewset.py

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from evaluation_app.filters import CompetencyFilter
from django_filters.rest_framework import DjangoFilterBackend
from evaluation_app.models import Competency, EmployeePlacement,EvalStatus
from evaluation_app.serializers.competency_serializer import CompetencySerializer
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, CanTouchObjOrComp
from evaluation_app.services.competency_math import recalculate_competency_weights
from django.db.models import Q
from rest_framework.response import Response
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
        action = self.action

        # LIST & RETRIEVE
        if action in ("list", "retrieve"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
            return [IsAuthenticated()]

        # CREATE / UPDATE / DELETE
        if action in ("create", "update", "partial_update"):
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
           
        
            if role == "EMP":
                return [CanTouchObjOrComp()]
            self.permission_denied(
                self.request,
                message="You cannot update this conpetency.",)

        if action == "destroy":
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]

            if role == "EMP":
                return [CanTouchObjOrComp()]
            
            self.permission_denied(
                self.request, 
                message="You cannot delete competency."
            )    
                
            
        # Everyone else forbidden
        self.permission_denied(self.request) 

        return super().get_permissions()
    def get_queryset(self):
        qs = Competency.objects.select_related("evaluation__employee__user")
        user = self.request.user

        if user.role in ("ADMIN", "HR"):
            return qs

        if user.role in ("HOD", "LM"):
            # only competencies for employees they manage
            return qs.filter(evaluation__employee__employee_placements__in=EmployeePlacement.objects.filter(
                Q(department__manager=user) |
                Q(sub_department__manager=user) |
                Q(section__manager=user) | 
                Q(sub_section__manager=user))).distinct()

        # regular employee only sees own
        emp = getattr(user, "employee_profile", None)
        if emp is None:
            return qs.none()
        return qs.filter(evaluation__employee=emp)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # For employees, check permission on the evaluation before creating
        if request.user.role == "EMP":
            evaluation = serializer.validated_data.get("evaluation")
            if evaluation:
                # Check if employee can add competencies to this evaluation
                emp = getattr(request.user, "employee_profile", None)
                if not emp or evaluation.employee != emp:
                    self.permission_denied(
                        request, 
                        message="You can only add competencies to your own evaluations."
                    )
                if evaluation.status != EvalStatus.SELF_EVAL:
                    self.permission_denied(
                        request, 
                        message="You can only add competencies during self-evaluation."
                    )
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
         
        obj = serializer.save()
        recalculate_competency_weights(obj.evaluation)
        obj.refresh_from_db(fields=["weight","updated_at"])    

    def perform_update(self, serializer):
        obj = serializer.save()
        recalculate_competency_weights(obj.evaluation)
        obj.refresh_from_db(fields=["weight","updated_at"])

 
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Competency deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    def perform_destroy(self, instance):
        evaluation = instance.evaluation
        super().perform_destroy(instance)
        recalculate_competency_weights(evaluation)        