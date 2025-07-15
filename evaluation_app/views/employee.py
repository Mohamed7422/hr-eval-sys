from rest_framework import viewsets, filters
from evaluation_app.models import Employee
from evaluation_app.serializers.employee_serilized import EmployeeSerializer
from evaluation_app.permissions import IsHR, IsAdmin, IsHOD, IsLineManager, IsSelfOrAdminHR


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):

    """
    * HR/Admin: list every employee.
    * Line-Manager: only employees in departments they manage.
    * Employee: only ‘me’.
    """

   # queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__name', 'user__email']
     
    def get_permissions(self):
        if self.action == "list":
            if self.request.user.role in ("HR", "Admin"):
               return [IsHR() | IsAdmin() | IsHOD()]
            elif self.request.user.role in ("LM", "HOD"):
                return [IsLineManager()| IsHOD()]
            else:
                # regular employee cannot list everybody
                self.permission_denied(
                    self.request, message="You do not have permission to view this list."
                )
        # retrieve permission (object-level)        
        return [IsSelfOrAdminHR]  
    
    def get_queryset(self):
        user = self.request.user
        qs = Employee.objects.select_related('user','company').prefetch_related("department")

        if user.role in ("HR", "Admin"):
            return qs
        if user.role in ("HOD", "LM"):
            # filter by department for HOD and Line Managers
            return qs.filter(department__manager=user).distinct()
        return qs.filter(user=user)


        