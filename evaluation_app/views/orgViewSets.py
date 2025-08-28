from evaluation_app.serializers.org_serializers import(
    CompanySerializer, DepartmentSerializer, SubDepartmentSerializer, SectionSerializer, SubSectionSerializer, EmployeePlacementSerializer
)
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager, IsSelfOrAdminHR, ReadOnlyOrAdminHR,IsAdminOrHR
from evaluation_app.models import Company, Department, SubDepartment, Section, SubSection, EmployeePlacement
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

# ──────────────────────────────────────────────────────────────────────────────

class SubDepartmentViewSet(viewsets.ModelViewSet):
    queryset = SubDepartment.objects.select_related("department", "manager")
    serializer_class = SubDepartmentSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields   = ["name", "department__name"]

    def get_permissions(self):
        # read-only for authenticated users, full access for Admin/HR
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [ReadOnlyOrAdminHR()]
        return [IsAuthenticated()]

class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.select_related("sub_department","manager")
    serializer_class = SectionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name","sub_department__name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [ReadOnlyOrAdminHR()]
        return [IsAuthenticated()]

class SubSectionViewSet(viewsets.ModelViewSet):
    queryset = SubSection.objects.select_related("section","manager")
    serializer_class = SubSectionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name","section__name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [ReadOnlyOrAdminHR()]
        return [IsAuthenticated()]

class EmployeePlacementViewSet(viewsets.ModelViewSet):
    queryset = EmployeePlacement.objects.select_related(
        "employee","company","department","sub_department","section","sub_section",
        "department__manager","sub_department__manager","section__manager","sub_section__manager",
        "employee__user"
    )
    serializer_class = EmployeePlacementSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["employee__user__name","employee__user__email","department__name","sub_department__name","section__name","sub_section__name"]

    def get_permissions(self):
        # Admin/HR can write; everyone authenticated can read
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [ReadOnlyOrAdminHR()]
        return [IsAuthenticated()]

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset()
        if u.role in ("ADMIN","HR"):
            return qs
        if u.role in ("HOD","LM"):
            return qs.filter(
                Q(department__manager=u) |
                Q(sub_department__manager=u) |
                Q(section__manager=u) |
                Q(sub_section__manager=u)
            ).distinct()
        # employee: only his own placements
        return qs.filter(employee__user=u)