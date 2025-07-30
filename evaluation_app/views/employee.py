from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from evaluation_app.models import Employee
from evaluation_app.serializers.employee_serilized import EmployeeSerializer
from evaluation_app.permissions import IsHR, IsAdmin, IsHOD, IsLineManager, IsSelfOrAdminHR


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
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__name', 'user__email']
     
    
    def get_permissions(self):
        role = self.request.user.role

        # ─── LIST ───────────────────────────────────────
        if self.action == 'list':
            if role in ('ADMIN','HR'):
                return [(IsAdmin|IsHR)()]
            if role in ('HOD','LM'):
                return [(IsHOD|IsLineManager)()]
            self.permission_denied(self.request, message="Cannot list all employees.")

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
        user = self.request.user
        qs   = Employee.objects.select_related('user','company').prefetch_related('departments')

        if user.role in ('ADMIN','HR'):
            return qs
        if user.role in ('HOD','LM'):
            # only those in departments they manage
            return qs.filter(departments__manager=user).distinct()
        # regular employee only sees self
        return qs.filter(user=user)
    
    def get_serializer_class(self):
        return EmployeeSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return Response(
            {"message": "Employee deleted successfully."}, status=status.HTTP_200_OK
        )   