
from rest_framework import serializers
from evaluation_app.models import Employee, EmployeePlacement, ManagerialLevel, JobType, BranchType
from evaluation_app.models import EmpStatus
from evaluation_app.utils import LabelChoiceField
from accounts.models import User

 
class EmployeeListSerializer(serializers.ModelSerializer):
   
 
    name         = serializers.CharField(source="user.name", read_only=True)
    email        = serializers.CharField(source="user.email", read_only=True)
    phone        = serializers.CharField(source="user.phone", allow_blank=True, read_only=True)
    country_code = serializers.CharField(source="user.country_code", allow_blank=True, read_only=True)
    avatar       = serializers.CharField(source="user.avatar", allow_blank=True, read_only=True)
    role         = serializers.CharField(source="user.role", read_only=True)
    position     = serializers.CharField(source="user.position", allow_blank=True, read_only=True)
    branch = LabelChoiceField(choices=BranchType.choices)
    location = serializers.CharField(allow_blank=True)
    managerial_level = LabelChoiceField(choices=ManagerialLevel.choices)
    job_type = LabelChoiceField(choices=JobType.choices)
    warnings = serializers.JSONField(source="warning", required=False)
    warnings_count = serializers.IntegerField(source="warning_count", read_only=True)
    status            = LabelChoiceField(choices=EmpStatus.choices)
    company_name = serializers.CharField(source="company.name", read_only=True, default=None)
    join_date         = serializers.DateField(format="%Y-%m-%d")
    department = serializers.SerializerMethodField(read_only=True)
    user_id    = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.all(),
        required=False

    )
    org_path   = serializers.SerializerMethodField()
    direct_manager = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [     
            "employee_id",
            "user_id",
            "name",
            "position",
            "branch",
            "location",
            "status",
            "role",
            "job_type",
            "managerial_level",
            "warnings",
            "org_path",
            "direct_manager",
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

    def _resolve_lineage(self, p: EmployeePlacement):
        dept = sdep = sec = ssec = None
        level = None

        if p.sub_section_id:
            level = "sub_section"
            ssec  = p.sub_section
            sec   = ssec.section if ssec else None
            sdep  = sec.sub_department if sec else None
            dept  = sdep.department if sdep else None

        elif p.section_id:
            level = "section"
            sec   = p.section
            sdep  = sec.sub_department if sec else None
            dept  = sdep.department if sdep else None

        elif p.sub_department_id:
            level = "sub_department"
            sdep  = p.sub_department
            dept  = sdep.department if sdep else None

        elif p.department_id:
            level = "department"
            dept  = p.department

    # choose the direct manager for the deepest available unit
        lm = (ssec.manager if ssec else
          sec.manager  if sec  else
          sdep.manager if sdep else
          dept.manager if dept else None)

        return level, dept, sdep, sec, ssec, lm
    
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

    def get_org_path(self, obj):
        p = self._latest_placement(obj)
        if not p:
            return ""
        _, dept, sdep, sec, ssec, _ = self._resolve_lineage(p)
          
        return " › ".join(u.name for u in (dept, sdep, sec, ssec) if u)
    

    def get_direct_manager(self, obj):
        p = self._latest_placement(obj)
        if not p:
            return None
        _, dept, sdep, sec, ssec, lm = self._resolve_lineage(p)
        if not lm:
            return None
        '''"id": str(lm.user_id),'''
        return lm.name 