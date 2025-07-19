from rest_framework import viewsets, filters
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
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]  # default fallback
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__name', 'user__email']
     
    def get_permissions(self):
        user_role = self.request.user.role
        # list permission (collection-level)
        if self.action == "list":
            if user_role in ("HR", "ADMIN"):
               return [(IsAdmin | IsHR)()]
            if user_role in ("LM", "HOD"):
                return [(IsLineManager | IsHOD)()]
            # regular employee → deny list-all
            self.permission_denied(
                self.request, message="You cannot list all employees."
            )

        # retrieve permission (object-level)  
        if self.action == "retrieve":      
           return [IsSelfOrAdminHR]  
        
        # default: no extra permissions
        return super().get_permissions()
    
    def get_queryset(self):
        user = self.request.user
        qs = Employee.objects.select_related('user','company').prefetch_related("departments")

        if user.role in ("HR", "ADMIN"):
            return qs
        if user.role in ("HOD", "LM"):
            # filter by department for HOD and Line Managers
            return qs.filter(department__manager=user).distinct()
        return qs.filter(user=user)


        