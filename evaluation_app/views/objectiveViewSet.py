from rest_framework import viewsets, status, filters
 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from evaluation_app.filters import ObjectiveFilter
from evaluation_app.models import Objective, EmployeePlacement, EvalStatus
from evaluation_app.serializers.objective_serializer import ObjectiveSerializer
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, CanTouchObjOrComp 
from django.db.models import Q 
from evaluation_app.services.objective_math import validate_objectives_constraints
import logging
from django.core.exceptions import ValidationError as DjangoValidationError 
from rest_framework.decorators import action 
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
            
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]
            
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
       # print(f" DEBUG = {settings.DEBUG}")
       # reset_queries() 
        #start = time.time()
        serializer  = self.get_serializer(data=request.data)
         
        #validation_time = time.time()
        serializer.is_valid(raise_exception=True)
        #print(f"⏱️ Validation: {time.time() - validation_time:.3f}s")

        
        checkCreateObjectivesForSelfEvaluation(self, request, serializer)


        obj =serializer.save() #triggers objective post_save signal to recalculate weights
        constraints_met = True
        warnings = []
        #pull in bulk update changes done by the signal
        #elapsed = time.time() - start 
        #logger.info(f"⏱️ Objective created in {elapsed:.3f}s")
        #print(f"⏱️ Objective created in {elapsed:.3f}s")  # Also print to console
        try:
            validate_objectives_constraints(obj.evaluation)
        except DjangoValidationError as e:
            logger.warning(f"Objectives constraints not fully met: {e}")
            constraints_met = False
            warnings.append(str(e))
        #obj.refresh_from_db(fields=["weight","updated_at"])  No need since we take weight manually.
        response_data  = serializer.data
        response_data ['constraints_met'] = constraints_met
        if warnings:
            response_data['warnings'] = warnings
        headers = self.get_success_headers(response_data )
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        obj =serializer.save() #triggers objective post_save signal to recalculate weights
        #pull in bulk update changes done by the signal
        try:
            validate_objectives_constraints(obj.evaluation)
        except DjangoValidationError as e:
            logger.warning(f"Objectives constraints not fully met: {e}")

        #obj.refresh_from_db(fields=["weight","updated_at"])
        data = self.get_serializer(obj).data
        return Response(data)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request,  *args, **kwargs):
        instance = self.get_object()
        user = request.user
        if user.role in ("HOD", "LM"):
            manages = EmployeePlacement.objects.filter(
                Q(department__manager=user) |
                Q(sub_department__manager=user) |
                Q(section__manager=user) |
                Q(sub_section__manager=user),
                employee=instance.evaluation.employee
            ).exists()
            if not manages:
                self.permission_denied(
                    request,
                    message="You cannot delete this objective."
                )
        evaluation = instance.evaluation        
        self.perform_destroy(instance)
        # Validate constraints after deletion
        try:
            validate_objectives_constraints(evaluation)
        except DjangoValidationError as e:
            logger.warning(
                f"After deleting objective, constraints not met: {e}. "
                f"User must add/adjust objectives."
            )
        
        return Response(
            {"message": "Objective deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=["post"], url_path="validate-constraints")
    def validate_constraints(self, request):
            """
            Validate that all objectives meet constraints for an evaluation.
            
            POST /api/objectives/validate-constraints/
            Body: {"evaluation_id": "uuid"}
            
            Returns: {"valid": true/false, "message": "..."}
            """
            evaluation_id = request.data.get("evaluation_id")
            
            if not evaluation_id:
                return Response(
                    {"error": "evaluation_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                from evaluation_app.models import Evaluation
                evaluation = Evaluation.objects.get(evaluation_id=evaluation_id)
            except Evaluation.DoesNotExist:
                return Response(
                    {"error": "Evaluation not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                validate_objectives_constraints(evaluation)
                return Response({
                    "valid": True,
                    "message": "All objectives meet constraints"
                })
            except DjangoValidationError as e:
                return Response({
                    "valid": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)    
   
    @action(detail=False, methods=["get"], url_path="evaluation-status/(?P<evaluation_id>[^/.]+)")
    def evaluation_status(self, request, evaluation_id=None):
        """
        Quick status check for an evaluation's objectives.
        
        GET /api/objectives/evaluation-status/{evaluation_id}/
        
        Returns:
        {
            "count": 3,
            "total_weight": 75.0,
            "needs": ["1 more objective", "25% more weight"]
        }
        """
        try:
            from evaluation_app.models import Evaluation
            evaluation = Evaluation.objects.get(evaluation_id=evaluation_id)
        except Evaluation.DoesNotExist:
            return Response(
                {"error": "Evaluation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        objectives = list(evaluation.objective_set.all())
        count = len(objectives)
        total_weight = sum(float(obj.weight or 0) for obj in objectives)
        
        needs = []
        if count < 4:
            needs.append(f"{4 - count} more objective(s)")
        elif count > 6:
            needs.append(f"Remove {count - 6} objective(s)")
        
        if abs(total_weight - 100) > 0.01:
            if total_weight < 100:
                needs.append(f"{round(100 - total_weight, 2)}% more weight")
            else:
                needs.append(f"Reduce weight by {round(total_weight - 100, 2)}%")
        
        return Response({
            "count": count,
            "total_weight": round(total_weight, 2),
            "ready": len(needs) == 0,
            "needs": needs if needs else ["All set! ✓"]
        })
        
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