# evaluation_app/serializers/employee_serializer.py

from rest_framework import serializers
from evaluation_app.models import (Employee, Department, Company, ManagerialLevel, EmpStatus, JobType
                                   , BranchType, EmployeePlacement)
from accounts.models import User
from accounts.serializers.user_serializer import UserCreateSerializer
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
                                         required=False,
                                         read_only=True)
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
    created_at        = serializers.DateTimeField(format="iso-8601",          read_only=True)
    updated_at        = serializers.DateTimeField(format="iso-8601",          read_only=True)

     # ─────── PLACEMENT (READ-ONLY) ─────────────────────
    #placement  = serializers.SerializerMethodField()
    org_path   = serializers.SerializerMethodField()
    direct_manager = serializers.SerializerMethodField()

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

    gender = serializers.CharField(source="user.gender", allow_blank=True, read_only=True)

    # ─────── WRITE‑ONLY HOOKS ──────────────────────────────────────
    
    # …or update user *fields* inline
    user_data  = UserCreateSerializer(
        source="user",
        write_only=True,
        required=False,
        partial=True,
    )
 
    
    # NEW: single department on create (write-only)
    department_id  = serializers.PrimaryKeyRelatedField(
        source="__seed_department", # virtual holder; not a real model field
        queryset=Department.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    # read-only fields derived from placement
    department = serializers.SerializerMethodField(read_only=True)
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

            # read-only
            "department",

            # write‑only
            "user_id","user_data",
            "company_id",
            "department_id", 
            "job_type","location","branch",
            "gender",
            
        ]
        read_only_fields = ("employee_id",)

    def get_department(self, obj): 
        # return the department of the first placement if any
        p = self._latest_placement(obj)
        return p.department.name if p and p.department else None
     
    # ---------- Placement helpers ----------
    def _latest_placement(self, obj):
        """Optimized to use prefetched data and reduce queries"""
        if hasattr(obj, "placements_cache") and obj.placements_cache:
            return obj.placements_cache[0]
            
        # If no cache, do one efficient query with all needed relations
        return (EmployeePlacement.objects
            .select_related(
                "department",
                "department__manager",
                "sub_department",
                "sub_department__manager",
                "section",
                "section__manager", 
                "sub_section",
                "sub_section__manager"
            )
            .filter(employee=obj)
            .order_by("-assigned_at")
            .first())
    

    def _resolve_lineage(self, p: EmployeePlacement):
        """Optimized hierarchy resolution using prefetched data"""
        if not p:
            return None, None, None, None, None, None

        # Start with deepest level and work up
        if p.sub_section_id:
            ssec = p.sub_section
            sec = ssec.section  # Already loaded via select_related
            sdep = sec.sub_department
            dept = sdep.department
            level = "sub_section"
            manager = ssec.manager
        
        elif p.section_id:
            ssec = None
            sec = p.section
            sdep = sec.sub_department
            dept = sdep.department
            level = "section"
            manager = sec.manager
            
        elif p.sub_department_id:
            ssec = sec = None
            sdep = p.sub_department
            dept = sdep.department
            level = "sub_department"
            manager = sdep.manager
            
        elif p.department_id:
            ssec = sec = sdep = None
            dept = p.department
            level = "department"
            manager = dept.manager
            
        else:
            return None, None, None, None, None, None

        return level, dept, sdep, sec, ssec, manager

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
        """Optimized org path calculation"""
        p = self._latest_placement(obj)
        if not p:
            return ""
            
        # Build path components only for existing levels
        path_parts = []
        if p.department:
            path_parts.append(p.department.name)
        if p.sub_department:
            path_parts.append(p.sub_department.name)
        if p.section:
            path_parts.append(p.section.name)
        if p.sub_section:
            path_parts.append(p.sub_section.name)
            
        return " › ".join(path_parts)

    def get_direct_manager(self, obj):
        """Optimized manager lookup"""
        p = self._latest_placement(obj)
        if not p:
            return None
            
        # Get manager from deepest level first
        manager = None
        if p.sub_section and p.sub_section.manager:
            manager = p.sub_section.manager
        elif p.section and p.section.manager:
            manager = p.section.manager
        elif p.sub_department and p.sub_department.manager:
            manager = p.sub_department.manager
        elif p.department and p.department.manager:
            manager = p.department.manager
            
        return manager.name if manager else None
    
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
        
        # pull seed inputs
        company = validated_data.pop("company", None) 
        seed_dept  = validated_data.pop("__seed_department", None)
        # Derive company from department if missing
        if company is None and seed_dept is not None:
            company = seed_dept.company

        employee = Employee.objects.create(
            user=user,
            company=company,
            **validated_data
        )   
        # auto-create the initial placement (employee + company [+ department])
        if company is not None:
            if seed_dept and seed_dept.company_id != company.pk:
                raise serializers.ValidationError("department_id does not belong to the provided/derived company.")
            EmployeePlacement.objects.get_or_create(
                employee=employee,
                defaults={"company": company, "department": seed_dept or None}
            )

        return employee


    def update(self, instance, validated_data):
        print("DEBUG validated_data:", validated_data) 
        # ignore any seed dept on update
        validated_data.pop("__seed_department", None)
        
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
         
        
        # 3) let DRF handle the rest (company_id, phone, avatar, managerial_level, status…)
        return super().update(instance, validated_data)





    # no need to override create() at all—
    # DRF will now do:
    #   validated_data = { 'user': <User>, 'company': <Company>, … }
    #   return Employee.objects.create(**validated_data)
