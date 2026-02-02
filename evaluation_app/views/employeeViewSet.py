from rest_framework import viewsets, filters, status, permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch, Q,Count, Exists, OuterRef
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from evaluation_app.models import Employee,EmployeePlacement,Evaluation,EvalStatus
from evaluation_app.serializers.employee_serilized import EmployeeSerializer
from evaluation_app.permissions import IsHR, IsAdmin, IsHOD, IsLineManager, IsSelfOrAdminHR, IsAdminOrHR
from evaluation_app.services.employee_importer import parse_employee_rows, import_employees
from evaluation_app.eval_filters.employee_filters import EmployeeFilter
from datetime import datetime
import logging, traceback
logger =  logging.getLogger(__name__)
 



class EmployeeViewSet(viewsets.ModelViewSet):

    """
    * HR/Admin: list every employee.
    * Line-Manager: only employees in departments they manage.
    * Employee: only ‘me’.
    """

   # queryset = Employee.objects.all()
    queryset = Employee.objects.select_related('user','company').prefetch_related('departments')
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]  # default fallback
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = EmployeeFilter
    search_fields = ['user__name',
                    'user__email',
                    'user__user_id',
                    'employee_code',
                    'company__name',
                    'user__role'] 
     
       
    
     
    
    def get_permissions(self):
        # Handle anonymous users (e.g., during schema generation)
        if not self.request.user.is_authenticated:
           return [IsAuthenticated()]
        role = self.request.user.role

        # ─── LIST ───────────────────────────────────────
        if self.action == 'list':
            if role in ('ADMIN','HR'):
                return [(IsAdmin|IsHR)()]
            if role in ('HOD','LM'):
                return [(IsHOD|IsLineManager)()]
            #self.permission_denied(self.request, message="Cannot list all employees.")
            return [IsAuthenticated()]

        # ─── RETRIEVE ───────────────────────────────────
        if self.action == 'retrieve':
            # allow employee to see their own, and Admin/HR see anyone
            return [IsSelfOrAdminHR()]

        # ─── UPDATE / PARTIAL_UPDATE ────────────────────
        if self.action in ('update','partial_update'):
            # Admin & HR get free reign ...
            if role in ('ADMIN','HR'):
                return [(IsAdmin|IsHR)()]
            # … HOD & LM only on people they manage
            if role in ('HOD','LM'):
                return [(IsHOD|IsLineManager)()]
            # everyone else forbidden
            self.permission_denied(self.request, message="You cannot update this employee.")

        # ─── DELETE ─────────────────────────────────────
        if self.action == 'destroy':
            if role in ('ADMIN','HR'):
                return [(IsAdmin|IsHR)()]
            self.permission_denied(self.request, message="You cannot delete employees.")

        # ─── CREATE ─────────────────────────────────────
        if self.action == 'create':
            if role in ('ADMIN','HR'):
                return [(IsAdmin|IsHR)()]
            self.permission_denied(self.request, message="You cannot create employees.")

        # fallback
        return super().get_permissions()

    def get_queryset(self):
    # Optimize placement queries with all needed relations
        latest_placements = (
            EmployeePlacement.objects
            .select_related(
                "company",
                "department",
                "department__manager",
                "sub_department",
                "sub_department__manager",
                "sub_department__department",
                "section",
                "section__manager",
                "section__sub_department__department",
                "sub_section",
                "sub_section__manager",
                "sub_section__section__sub_department__department"
            )
            .order_by('-assigned_at')
        )
       
        # Base queryset with essential relations
        params = getattr(self.request, "query_params", {})
        user_filter = params.get("user_id") or params.get("employee_id")
        
        # Only prefetch evaluations when retrieving specific employee(s)
        include_evaluations = (self.action != "list") or bool(user_filter)

        prefetches = [
            Prefetch(
                "employee_placements",
                queryset=latest_placements,
                to_attr="placements_cache"
            ),
        ]
        # Prefetch all evaluations for pending calculation
        if include_evaluations:

            all_evals_qs = (
                Evaluation.objects
                .exclude(status=EvalStatus.SELF_EVAL)
                .only('period', 'status') #removed evaluation id
                .order_by('period')
            )
            prefetches.append(
                Prefetch(
                    "evaluations",
                    queryset=all_evals_qs,
                    to_attr="all_evaluations_cache"
                )
            )
        
        current_year = datetime.now().year
        current_year_periods = [f"{current_year}-Mid", f"{current_year}-End"]
    
        qs = (Employee.objects
            .select_related('user', 'company')
            .prefetch_related(*prefetches)
            .annotate(
                 # Count drafts for Mid periods (current year only)
                draft_count_mid=Count(
                    'evaluations',
                    filter=Q(evaluations__status=EvalStatus.DRAFT) &
                        Q(evaluations__period=f"{current_year}-Mid")
                ),
                # Count drafts for End periods (current year only)
                draft_count_end=Count(
                    'evaluations',
                    filter=Q(evaluations__status=EvalStatus.DRAFT) &
                        Q(evaluations__period=f"{current_year}-End")
                ),
                # Check if current year periods exist
                has_current_mid=Exists(
                    Evaluation.objects.filter(
                        employee=OuterRef('pk'),
                        period=f"{current_year}-Mid"
                    )
                ),
                has_current_end=Exists(
                    Evaluation.objects.filter(
                        employee=OuterRef('pk'),
                        period=f"{current_year}-End"
                    )
                )
            )
        )

        user = self.request.user

        # Role-based filtering
        if user.role in ('ADMIN', 'HR'):
            return qs
        elif user.role in ('HOD', 'LM'):
            # Filter by departments they manage at any level
            managed_employees = qs.filter(
                employee_placements__in=EmployeePlacement.objects.filter(
                    Q(department__manager=user) |
                    Q(sub_department__manager=user) |
                    Q(section__manager=user) |
                    Q(sub_section__manager=user)
                )
            ).distinct()
            return managed_employees
        else:
            # Regular employee sees only themselves
            return qs.filter(user=user)

 

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return Response(
            {"message": "Employee deleted successfully."}, status=status.HTTP_200_OK
        )   
    
    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        permission_classes=[permissions.IsAuthenticated, IsAdminOrHR],
    )
    def import_employees(self, request, *args, **kwargs):

        try:

            dry_run = request.query_params.get("dry_run") == "true"
            update_existing = request.query_params.get("update_existing", "true").lower() == "true"
            upsert_by_code = request.query_params.get("upsert_by_code", "true").lower() == "true"

            
            rows = parse_employee_rows(request)
            logger.info(f"Rows parsed: {len(rows)}")

            result = import_employees(rows, 
                                    dry_run=dry_run,
                                    update_existing=update_existing,
                                    upsert_by_code=upsert_by_code)
            
            logger.info(f"Import result: {result.get('status')}")

            if result.get("status") == "invalid":
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            return Response(result,
                            status=status.HTTP_200_OK if dry_run else status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"IMPORT FAILED: {type(e).__name__}: {str(e)}")
            logger.error("=" * 80)
            logger.error(traceback.format_exc())
            logger.error("=" * 80)
            
            return Response({
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "detail": "Import failed - check server logs for details"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)