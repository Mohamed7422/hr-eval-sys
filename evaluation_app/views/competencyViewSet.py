# evaluation_app/views/competency_viewset.py

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from evaluation_app.filters import CompetencyFilter
from django_filters.rest_framework import DjangoFilterBackend
from evaluation_app.models import Competency, EmployeePlacement,EvalStatus, CompetencyCategory
from evaluation_app.serializers.competency_serializer import CompetencySerializer
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, CanTouchObjOrComp
from evaluation_app.services.competency_math import  validate_competencies_constraints
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework.decorators import action
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
            
            if role in ("HOD", "LM"):
                return [(IsHOD|IsLineManager)()]

            if role == "EMP":
                return [CanTouchObjOrComp()]
            
            self.permission_denied(
                self.request, 
                message="You cannot delete competency."
            )    

        return [IsAuthenticated()]
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
        
        
        comp = serializer.save()
        
        # Check constraints (optional - doesn't block creation)
        constraints_met = True
        warnings = []
        try:
            validate_competencies_constraints(comp.evaluation)
        except DjangoValidationError as e:
            constraints_met = False
            warnings.append(str(e))
        
        # Return response with validation status
        data = self.get_serializer(comp).data
        data['constraints_met'] = constraints_met
        if warnings:
            data['warnings'] = warnings
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """
        Update a competency.
        
        Weight is recalculated automatically based on:
        Weight = Category Weight / Count in Category
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Save competency
        # No need to recalculate weights - they're calculated dynamically
        comp = serializer.save()
        
        # Check constraints (optional - doesn't block update)
        constraints_met = True
        warnings = []
        try:
            validate_competencies_constraints(comp.evaluation)
        except DjangoValidationError as e:
            constraints_met = False
            warnings.append(str(e))
        
        # Return response
        data = self.get_serializer(comp).data
        data['constraints_met'] = constraints_met
        if warnings:
            data['warnings'] = warnings
        
        return Response(data)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
 
    def destroy(self, request, *args, **kwargs):
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
                    message="You cannot delete this competency."
                )
        evaluation = instance.evaluation        
        self.perform_destroy(instance)
        try:
            validate_competencies_constraints(evaluation)
        except DjangoValidationError as e:
            # Constraints might not be met after deletion
            # This is informational only
            pass
        
        return Response(
            {"message": "Competency deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=["post"], url_path="validate-constraints")
    def validate_constraints(self, request):
        """
        Validate that all competencies meet constraints for an evaluation.
        
        POST /api/competencies/validate-constraints/
        Body: {"evaluation_id": "uuid"}
        
        Note: Competencies are OPTIONAL. If none exist, validation passes.
        Note: Only categories with weight > 0 are required.
              Example: EXECUTIVE level has functional_weight=0, so FUNCTIONAL not required.
        
        Returns detailed validation status:
        {
            "valid": true/false,
            "has_competencies": true/false,
            "required_categories": ["CORE", "LEADERSHIP"],
            "has_core": true/false,
            "has_leadership": true/false,
            "has_functional": true/false,
            "messages": [...]
        }
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
        
        # Get current competencies
        competencies = list(evaluation.competency_set.all())
        has_competencies = len(competencies) > 0
        
        # If no competencies, that's valid (they're optional)
        if not has_competencies:
            return Response({
                "valid": True,
                "has_competencies": False,
                "required_categories": [],
                "has_core": False,
                "has_leadership": False,
                "has_functional": False,
                "levels_valid": True,
                "total_count": 0,
                "messages": [
                    "ℹ️ No competencies added (competencies are optional)"
                ],
                "ready_for_submission": True
            })
        
        # Get category weights to determine which categories are required
        from evaluation_app.services.competency_math import category_weights_for_evaluation
        category_weights = category_weights_for_evaluation(evaluation)
        
        # Determine which categories are required (weight > 0)
        required_categories = []
        if category_weights.get(CompetencyCategory.CORE, 0) > 0:
            required_categories.append("CORE")
        if category_weights.get(CompetencyCategory.LEADERSHIP, 0) > 0:
            required_categories.append("LEADERSHIP")
        if category_weights.get(CompetencyCategory.FUNCTIONAL, 0) > 0:
            required_categories.append("FUNCTIONAL")
        
        # Check which categories are present
        categories = set(comp.category for comp in competencies)
        has_core = CompetencyCategory.CORE in categories
        has_leadership = CompetencyCategory.LEADERSHIP in categories
        has_functional = CompetencyCategory.FUNCTIONAL in categories
        
        messages = []
        levels_valid = True
        categories_valid = True
        
        # Check levels
        for comp in competencies:
            if comp.actual_level < 0 or comp.actual_level > 4:
                levels_valid = False
                messages.append(f"✗ '{comp.name}' actual level {comp.actual_level} is outside 0-4 range")
            
            if comp.required_level < 0 or comp.required_level > 4:
                levels_valid = False
                messages.append(f"✗ '{comp.name}' required level {comp.required_level} is outside 0-4 range")
        
        if levels_valid and len(competencies) > 0:
            messages.append("✓ All competency levels are valid (0-4)")
        
        # Check categories (only those with non-zero weights)
        # CORE
        if "CORE" in required_categories:
            if has_core:
                core_count = len([c for c in competencies if c.category == CompetencyCategory.CORE])
                messages.append(f"✓ Has CORE competencies ({core_count})")
            else:
                categories_valid = False
                messages.append(f"✗ Missing CORE competencies (required: weight={category_weights.get(CompetencyCategory.CORE, 0)}%)")
        else:
            if has_core:
                core_count = len([c for c in competencies if c.category == CompetencyCategory.CORE])
                messages.append(f"ℹ️ Has CORE competencies ({core_count}) but weight is 0%")
            else:
                messages.append("ℹ️ CORE not required (weight is 0%)")
        
        # LEADERSHIP
        if "LEADERSHIP" in required_categories:
            if has_leadership:
                leadership_count = len([c for c in competencies if c.category == CompetencyCategory.LEADERSHIP])
                messages.append(f"✓ Has LEADERSHIP competencies ({leadership_count})")
            else:
                categories_valid = False
                messages.append(f"✗ Missing LEADERSHIP competencies (required: weight={category_weights.get(CompetencyCategory.LEADERSHIP, 0)}%)")
        else:
            if has_leadership:
                leadership_count = len([c for c in competencies if c.category == CompetencyCategory.LEADERSHIP])
                messages.append(f"ℹ️ Has LEADERSHIP competencies ({leadership_count}) but weight is 0%")
            else:
                messages.append("ℹ️ LEADERSHIP not required (weight is 0%)")
        
        # FUNCTIONAL
        if "FUNCTIONAL" in required_categories:
            if has_functional:
                functional_count = len([c for c in competencies if c.category == CompetencyCategory.FUNCTIONAL])
                messages.append(f"✓ Has FUNCTIONAL competencies ({functional_count})")
            else:
                categories_valid = False
                messages.append(f"✗ Missing FUNCTIONAL competencies (required: weight={category_weights.get(CompetencyCategory.FUNCTIONAL, 0)}%)")
        else:
            if has_functional:
                functional_count = len([c for c in competencies if c.category == CompetencyCategory.FUNCTIONAL])
                messages.append(f"ℹ️ Has FUNCTIONAL competencies ({functional_count}) but weight is 0%")
            else:
                messages.append("ℹ️ FUNCTIONAL not required (weight is 0%)")
        
        all_valid = categories_valid and levels_valid
        
        return Response({
            "valid": all_valid,
            "has_competencies": True,
            "required_categories": required_categories,
            "category_weights": {
                "core": category_weights.get(CompetencyCategory.CORE, 0),
                "leadership": category_weights.get(CompetencyCategory.LEADERSHIP, 0),
                "functional": category_weights.get(CompetencyCategory.FUNCTIONAL, 0)
            },
            "has_core": has_core,
            "has_leadership": has_leadership,
            "has_functional": has_functional,
            "levels_valid": levels_valid,
            "categories_valid": categories_valid,
            "total_count": len(competencies),
            "messages": messages,
            "ready_for_submission": all_valid
        })

    @action(detail=False, methods=["get"], url_path="evaluation-status/(?P<evaluation_id>[^/.]+)")
    def evaluation_status(self, request, evaluation_id=None):
        """
        Quick status check for an evaluation's competencies.
        
        GET /api/competencies/evaluation-status/{evaluation_id}/
        
        Note: Competencies are OPTIONAL. If none exist, returns ready=true.
        Note: Only checks categories with weight > 0.
        
        Returns:
        {
            "has_competencies": true/false,
            "required_categories": ["CORE", "LEADERSHIP"],
            "total_count": 5,
            "core_count": 2,
            "leadership_count": 3,
            "functional_count": 0,
            "ready": true,
            "needs": []
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
        
        competencies = list(evaluation.competency_set.all())
        
        # If no competencies, that's fine - they're optional
        if len(competencies) == 0:
            return Response({
                "has_competencies": False,
                "required_categories": [],
                "total_count": 0,
                "core_count": 0,
                "leadership_count": 0,
                "functional_count": 0,
                "ready": True,
                "needs": ["No competencies (competencies are optional)"]
            })
        
        # Get category weights to determine which categories are required
        from evaluation_app.services.competency_math import category_weights_for_evaluation
        category_weights = category_weights_for_evaluation(evaluation)
        
        # Determine which categories are required (weight > 0)
        required_categories = []
        if category_weights.get(CompetencyCategory.CORE, 0) > 0:
            required_categories.append("CORE")
        if category_weights.get(CompetencyCategory.LEADERSHIP, 0) > 0:
            required_categories.append("LEADERSHIP")
        if category_weights.get(CompetencyCategory.FUNCTIONAL, 0) > 0:
            required_categories.append("FUNCTIONAL")
        
        # Count by category
        core_count = len([c for c in competencies if c.category == CompetencyCategory.CORE])
        leadership_count = len([c for c in competencies if c.category == CompetencyCategory.LEADERSHIP])
        functional_count = len([c for c in competencies if c.category == CompetencyCategory.FUNCTIONAL])
        
        needs = []
        
        # Only check required categories (those with non-zero weights)
        if "CORE" in required_categories and core_count == 0:
            needs.append(f"Add at least one CORE competency (weight: {category_weights.get(CompetencyCategory.CORE, 0)}%)")
        
        if "LEADERSHIP" in required_categories and leadership_count == 0:
            needs.append(f"Add at least one LEADERSHIP competency (weight: {category_weights.get(CompetencyCategory.LEADERSHIP, 0)}%)")
        
        if "FUNCTIONAL" in required_categories and functional_count == 0:
            needs.append(f"Add at least one FUNCTIONAL competency (weight: {category_weights.get(CompetencyCategory.FUNCTIONAL, 0)}%)")
        
        return Response({
            "has_competencies": True,
            "required_categories": required_categories,
            "category_weights": {
                "core": category_weights.get(CompetencyCategory.CORE, 0),
                "leadership": category_weights.get(CompetencyCategory.LEADERSHIP, 0),
                "functional": category_weights.get(CompetencyCategory.FUNCTIONAL, 0)
            },
            "total_count": len(competencies),
            "core_count": core_count,
            "leadership_count": leadership_count,
            "functional_count": functional_count,
            "ready": len(needs) == 0,
            "needs": needs if needs else ["All set! ✓"]
        })






























           