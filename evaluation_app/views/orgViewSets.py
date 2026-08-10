from evaluation_app.serializers.org_serializers import(
    CompanySerializer, DepartmentSerializer
)
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, IsSelfOrAdminHR, ReadOnlyOrAdminHR,IsAdminOrHR
from evaluation_app.models import Company, Department
from rest_framework import viewsets, filters, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by("name")
    serializer_class = CompanySerializer
    permission_classes = [ReadOnlyOrAdminHR] # read-only for authenticated users, full access for Admin/HR
    print("CompanyViewSet permissions:", permission_classes)

    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "industry"]
     # … list / create / retrieve / update / destroy are inherited …

    @action(
      detail=False, #collection-level
      methods=["post"],
      url_path="create",  #  → /companies/create/
      permission_classes=[permissions.IsAuthenticated,IsAdminOrHR]
    )
    def create_company(self, request, *args, **kwargs):
        """
        Custom action to create a new company.
        Only Admin or HR can create a company.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)



class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("company", "manager")
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.SearchFilter]
    filterset_fields = ["company"]
    search_fields = ["name"]

    @action(
        detail=False,  # collection-level
        methods=["post"],
        url_path="create",  # → /departments/create/
        permission_classes=[permissions.IsAuthenticated, IsAdminOrHR])
    
    def create_department(self, request, *args, **kwargs):
        """
        Custom action to create a new department.
        Only Admin or HR can create a department.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #self.perform_create(serializer)
        #headers = self.get_success_headers(serializer.data)
         # this will pass through company & name & employee_count,
        # and manager=None if not in request.data
        dept = serializer.save()

        return Response(
            DepartmentSerializer(dept).data,
            status=status.HTTP_201_CREATED
        )
 
    def get_queryset(self):
        qs =  super().get_queryset()
        u = self.request.user
        if u.role in ("Admin", "HR", "ADMIN"):
            return qs
        if u.role in ("HOD", "LM"):
            return qs.filter(manager=u)
        return qs.none() # regular employees cannot access departments
    
    def get_permissions(self):
        if self.action in ("list","retrieve"):
            return [IsAuthenticated()] # read-only for all authenticated users
        return [(IsAdmin | IsHR)()]  # write permissions for Admin & HR only
    