from rest_framework import viewsets, filters, status, permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from evaluation_app.models import Employee,EmployeePlacement
from evaluation_app.serializers.employee_serilized import EmployeeSerializer
from evaluation_app.permissions import IsHR, IsAdmin, IsHOD, IsLineManager, IsSelfOrAdminHR, IsAdminOrHR
from evaluation_app.services.employee_importer import parse_employee_rows, import_employees
from evaluation_app.eval_filters.employee_filters import EmployeeFilter



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
        qs = (Employee.objects
            .select_related('user', 'company')
            .prefetch_related(
                Prefetch(
                    "employee_placements",
                    queryset=latest_placements,
                    to_attr="placements_cache"
                )
            ))

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
        dry_run = request.query_params.get("dry_run") == "true"
        update_existing = request.query_params.get("update_existing", "true").lower() == "true"
        upsert_by_code = request.query_params.get("upsert_by_code", "true").lower() == "true"

        try:
            rows = parse_employee_rows(request)
        except Exception as e:
            import logging 
            logging.getLogger("django.request").exception("Employee import failed")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        result = import_employees(rows, 
                                  dry_run=dry_run,
                                  update_existing=update_existing,
                                  upsert_by_code=upsert_by_code)

        if result.get("status") == "invalid":
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result,
                        status=status.HTTP_200_OK if dry_run else status.HTTP_201_CREATED)
    
    