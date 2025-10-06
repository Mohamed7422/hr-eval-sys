
from rest_framework import serializers
from evaluation_app.models import Employee, EmployeePlacement 
from evaluation_app.models import EmpStatus
from evaluation_app.utils import LabelChoiceField


 
class EmployeeListSerializer(serializers.ModelSerializer):
   
 
    name         = serializers.CharField(source="user.name", read_only=True)
    email        = serializers.CharField(source="user.email", read_only=True)
    phone        = serializers.CharField(source="user.phone", allow_blank=True, read_only=True)
    country_code = serializers.CharField(source="user.country_code", allow_blank=True, read_only=True)
    avatar       = serializers.CharField(source="user.avatar", allow_blank=True, read_only=True)
    role         = serializers.CharField(source="user.role", read_only=True)
    position     = serializers.CharField(source="user.position", allow_blank=True, read_only=True)
    managerial_level = serializers.CharField(source="user.managerial_level", read_only=True)
    status       = serializers.CharField(source="user.status", read_only=True)
    warnings_count = serializers.IntegerField(source="warning_count", read_only=True)
    status            = LabelChoiceField(choices=EmpStatus.choices)
    company_name = serializers.CharField(source="company.name", read_only=True, default=None)
    join_date         = serializers.DateField(format="%Y-%m-%d")
    department = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Employee
        fields = [     
              "name",
            "position",
            "status",
            "role",
            "managerial_level",
            "warnings_count",
            "email",
            "phone",
            "country_code",
            "avatar",
            "join_date",
            "company_name",
            "department",
        ]
        read_only_fields = fields

     


    def get_department(self, obj): 
        # return the department of the first placement if any
        p = self._latest_placement(obj)
        return p.department.name if p and p.department else None

    def _latest_placement(self, obj):
        # use prefetch cache if present
        if hasattr(obj, "placements_cache") and obj.placements_cache:
            return obj.placements_cache[0]
        return (
            EmployeePlacement.objects
            .select_related(
                "company",
                "department",
                "sub_department__department",
                "section__sub_department__department",
                "sub_section__section__sub_department__department",
            )
            .filter(employee=obj)
            .order_by("-assigned_at")
            .first()
        )

     