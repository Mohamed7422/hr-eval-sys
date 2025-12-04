from rest_framework import viewsets, status, filters
 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from evaluation_app.filters import ObjectiveFilter
from evaluation_app.models import Objective, EmployeePlacement, EvalStatus
from evaluation_app.serializers.objective_serializer import ObjectiveSerializer
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, CanTouchObjOrComp 
from django.db.models import Q 
import time
import logging
from django.conf import settings
from django.db import reset_queries
logger =  logging.getLogger(__name__)
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
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
            
            if role == "EMP":
                return [CanTouchObjOrComp()]
            self.permission_denied(
                self.request,
                message="You cannot update this objective.",)

        # ─── DESTROY ───────────────────────────────────────
        if action == "destroy":
            if role in ("ADMIN", "HR"):
                return [(IsAdmin|IsHR)()]
            
            if role == "EMP":
                return [CanTouchObjOrComp()]
            
            self.permission_denied(
                self.request, 
                message="You cannot delete objectives."
            )

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
        
        
        emp = getattr(user, "employee_profile", None)
        if emp is None:
            return qs.none()
        return qs.filter(evaluation__employee=emp)
        
         


    def create(self, request, *args, **kwargs):
        print(f" DEBUG = {settings.DEBUG}")
        reset_queries() 
        start = time.time()
        ser = self.get_serializer(data=request.data)
        validation_time = time.time()
        ser.is_valid(raise_exception=True)
        print(f"⏱️ Validation: {time.time() - validation_time:.3f}s")

        
        checkCreateObjectivesForSelfEvaluation(self, request, ser)


        obj =ser.save() #triggers objective post_save signal to recalculate weights
        #pull in bulk update changes done by the signal
        elapsed = time.time() - start 
        logger.info(f"⏱️ Objective created in {elapsed:.3f}s")
        print(f"⏱️ Objective created in {elapsed:.3f}s")  # Also print to console
    
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

    def destroy(self, request,  *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "message": "Objective deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )

        
def checkCreateObjectivesForSelfEvaluation(self, request, ser,):
     if request.user.role == "EMP":
        evaluation_id = ser.validated_data.get("evaluation")
        if evaluation_id:
            emp = getattr(request.user, "employee_profile", None)
            
            if not emp or evaluation_id.employee != emp:
                self.permission_denied(
                    request,
                    message="You cannot create objectives for this evaluation.",
                )
            if evaluation_id.status != EvalStatus.SELF_EVAL:
                self.permission_denied(
                    request,
                    message="You cannot create objectives for this evaluation.",
                )