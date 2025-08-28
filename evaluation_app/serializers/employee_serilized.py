# evaluation_app/serializers/employee_serializer.py

from rest_framework import serializers
from evaluation_app.models import (Employee, Department, Company, ManagerialLevel, EmpStatus, JobType
                                   , BranchType, SubDepartment, Section, SubSection, EmployeePlacement)
from accounts.models import User
from accounts.serializers.user_serializer import UserCreateSerializer
from evaluation_app.serializers.org_serializers import CompanySerializer, DepartmentSerializer
from evaluation_app.utils import LabelChoiceField
class EmployeeSerializer(serializers.ModelSerializer):
    # READ: show full user data
    #user = UserCreateSerializer(read_only=True)
     # ─────── FLATTENED USER FIELDS ─────────────────────
    name              = serializers.CharField(source="user.name", read_only=True)
    email             = serializers.CharField(source="user.email", read_only=True)
    phone             = serializers.CharField(source="user.phone", allow_blank=True, read_only=True)
    country_code      = serializers.CharField(source="user.country_code", allow_blank=True, read_only=True)
    avatar            = serializers.CharField(source="user.avatar", allow_blank=True, read_only=True)
    role              = LabelChoiceField(source="user.role", 
                                         choices=User._meta.get_field("role").choices,
                                         required=False)
    position          = serializers.CharField(source="user.position", allow_blank=True, read_only=True)


     # ─────── CHOICE DISPLAY & RELATED FIELDS ───────────────────────
    managerial_level = LabelChoiceField(choices=ManagerialLevel.choices)
    status            = LabelChoiceField(choices=EmpStatus.choices)
    employee_code     = serializers.CharField(allow_blank=True, required=False)
    warnings = serializers.JSONField(source="warning", required=False)
    warnings_count = serializers.IntegerField(source="warning_count", read_only=True)
    job_type = LabelChoiceField(choices=JobType.choices)
    location = serializers.CharField(allow_blank=True)
    branch = LabelChoiceField(choices=BranchType.choices)
    company_name      = serializers.CharField(source="company.name", read_only=True)
    #department      = serializers.SlugRelatedField(source="departments", many=True, slug_field="name", read_only=True)
     # ─────── TIMESTAMPS / DATES ────────────────────────────────────
    join_date         = serializers.DateField(format="%Y-%m-%d")
    created_at        = serializers.DateTimeField(format="iso‑8601",          read_only=True)
    updated_at        = serializers.DateTimeField(format="iso‑8601",          read_only=True)

     # ─────── PLACEMENT (READ-ONLY) ─────────────────────
    #placement  = serializers.SerializerMethodField()
    org_path   = serializers.SerializerMethodField()
    direct_manager = serializers.SerializerMethodField(source="get_direct_manager")

    # still expose the raw IDs if the front‑end needs them
    company_id = serializers.PrimaryKeyRelatedField(
        source="company",
        queryset=Company.objects.all(),
        required=False,
    )
    # Read / Write Reassign to an existing user by ID…
    user_id    = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.all(),
        required=False

    )

    # ─────── WRITE‑ONLY HOOKS ──────────────────────────────────────
    
    # …or update user *fields* inline
    user_data  = UserCreateSerializer(
        source="user",
        write_only=True,
        required=False,
        partial=True,
    )
 
    
    # Reassign departments by IDs
    departments_ids = serializers.PrimaryKeyRelatedField(
        source="departments",
        many=True,
        queryset=Department.objects.all(),
        write_only=True,
        required=False,
    )
    class Meta:
        model  = Employee
        fields = [
             # primary key
            "employee_id",
            "employee_code",

            # flattened-position R/W
            "name","email","phone","country_code","warnings","warnings_count","avatar","role","position",
            "managerial_level","status",

            "company_name","org_path","direct_manager",
            "join_date","created_at","updated_at",

            # write‑only
            "user_id","user_data",
            "company_id",
            "departments_ids", #deprecated
            "job_type","location","branch",
        ]
        read_only_fields = ("employee_id",)

    #def get_department(self, obj):
       #     name = obj.departments.all().values_list("name", flat=True)
       #     return ", ".join(name) # e.g. "Dev, QA, HR"
        
    # ---------- Placement helpers ----------
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

    def _resolve_lineage(self, p: EmployeePlacement):
        dept = sdep = sec = ssec = None
        level = None

        if p.department_id:
            level, dept = "department", p.department
        elif p.sub_department_id:
            level, sdep = "sub_department", p.sub_department
            dept = sdep.department if sdep else None
        elif p.section_id:
            level, sec = "section", p.section
            sdep = sec.sub_department if sec else None
            dept = sdep.department if sdep else None
        elif p.sub_section_id:
            level, ssec = "sub_section", p.sub_section
            sec  = ssec.section if ssec else None
            sdep = sec.sub_department if sec else None
            dept = sdep.department if sdep else None

        # who is the LM for this unit?
        lm = (ssec.manager if ssec else
              sec.manager if sec else
              sdep.manager if sdep else
              dept.manager if dept else None)

        return level, dept, sdep, sec, ssec, lm

    def get_placement(self, obj):
        p = self._latest_placement(obj)
        if not p:
            return None

        level, dept, sdep, sec, ssec, lm = self._resolve_lineage(p)
        return {
            "placement_id": str(p.placement_id),
            "level": level,  # "department" | "sub_department" | "section" | "sub_section"
            "company": (
                {"id": str(p.company_id), "name": p.company.name} if p.company_id else None
            ),
            "department": (
                {"id": str(dept.department_id), "name": dept.name} if dept else None
            ),
            "sub_department": (
                {"id": str(sdep.sub_department_id), "name": sdep.name} if sdep else None
            ),
            "section": (
                {"id": str(sec.section_id), "name": sec.name} if sec else None
            ),
            "sub_section": (
                {"id": str(ssec.sub_section_id), "name": ssec.name} if ssec else None
            ),
        }

    def get_org_path(self, obj):
        p = self._latest_placement(obj)
        if not p:
            return ""
        level, dept, sdep, sec, ssec, _ = self._resolve_lineage(p)
        parts = [x for x in [
            dept.name if dept else None,
            sdep.name if sdep else None,
            sec.name  if sec  else None,
            ssec.name if ssec else None,
        ] if x]
        return " › ".join(parts)

    def get_direct_manager(self, obj):
        p = self._latest_placement(obj)
        if not p:
            return None
        _, dept, sdep, sec, ssec, lm = self._resolve_lineage(p)
        if not lm:
            return None
        '''"id": str(lm.user_id),'''
        return lm.name
    
    def create(self, validated_data):
        user_payload = validated_data.pop("user", None)

        if isinstance(user_payload, User):
            # Case 1: attach to existing user
            user = user_payload

        elif isinstance(user_payload, dict):
            # Case 2: create a new User
            password = user_payload.pop("password", None)
            user = User.objects.create_user(
                username = user_payload["username"],
                email    = user_payload.get("email", ""),
                password = password,
                **{k: v for k, v in user_payload.items()
                   if k not in ("username", "email")}
            )

        else:
            raise serializers.ValidationError(
                "Either ‘user_id’ or full ‘user_data’ must be provided."
            )
        company = validated_data.pop("company") 
        departments = validated_data.pop("departments", [])
        employee = Employee.objects.create(
            user=user,
            company=company,
            **validated_data
        )   
        if departments:
            employee.departments.set(departments)

        return employee    


    def update(self, instance, validated_data):
        print("DEBUG validated_data:", validated_data) 
   
        # 1) nested user update?
        user_payload = validated_data.pop("user", None)
        if user_payload:
            print("DEBUG user_payload:", user_payload)
            user_serializer = UserCreateSerializer(
                instance=instance.user,
                data=user_payload,
                partial=True
            )
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()
         
        # 2) m2m departments?
        if "departments" in validated_data:
            instance.departments.set(validated_data.pop("departments"))

        # 3) let DRF handle the rest (company_id, phone, avatar, managerial_level, status…)
        return super().update(instance, validated_data)





    # no need to override create() at all—
    # DRF will now do:
    #   validated_data = { 'user': <User>, 'company': <Company>, … }
    #   return Employee.objects.create(**validated_data)
