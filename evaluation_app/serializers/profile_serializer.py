# profiles/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model


from evaluation_app.models import (
    Employee, EmployeePlacement, ManagerialLevel, EmpStatus, JobType, BranchType
)
from evaluation_app.utils import LabelChoiceField

User = get_user_model()

USER_EDITABLE = {"name", "phone", "country_code", "avatar", "position", "gender"}
EMP_EDITABLE  = {"location", "branch", "job_type"}  # keep employment updates modest/safe


class MyProfileSerializer(serializers.ModelSerializer):
    # ---- User fields (base model = User) ----
    role = LabelChoiceField(choices=User._meta.get_field("role").choices, read_only=True)
    
    gender = LabelChoiceField(choices=User._meta.get_field("gender").choices, required=False)
    # ---- Employment fields (conditionally shown) ----
    employee_id      = serializers.UUIDField(required=False, read_only=True)
    managerial_level = LabelChoiceField(choices=ManagerialLevel.choices, required=False)
    status           = LabelChoiceField(choices=EmpStatus.choices, required=False)
    employee_code    = serializers.CharField(required=False, allow_blank=True)
    job_type         = LabelChoiceField(choices=JobType.choices, required=False)
    location         = serializers.CharField(required=False, allow_blank=True)
    branch           = LabelChoiceField(choices=BranchType.choices, required=False)
    join_date        = serializers.DateField(required=False)

    company_id       = serializers.UUIDField(required=False, read_only=True)
    company_name     = serializers.CharField(required=False, read_only=True)

    department       = serializers.CharField(required=False, read_only=True)
    direct_manager   = serializers.CharField(required=False, read_only=True)
    org_path         = serializers.CharField(required=False, read_only=True)
     


    class Meta:
        model  = User
        # Only user fields here; employment fields are added manually in to_representation
        fields = [
            # User (read/update, except role/password)
            "user_id", "username", "email", "name", "phone", "country_code",
            "avatar", "role", "position", "gender",
            "is_default_password", "password_last_changed",
            "created_at", "updated_at",

            # Employment (conditionally added)
            "employee_id", "managerial_level", "status", "employee_code",
            "job_type", "location", "branch", "join_date",
            "company_id", "company_name",
            "department", "direct_manager", "org_path" 
        ]
        read_only_fields = (
            "user_id", "role",
            "is_default_password", "password_last_changed",
            "created_at", "updated_at",
            "employee_id","company_id","company_name","department","direct_manager","org_path",
            "join_date","managerial_level","status","employee_code"   # if self-edit should not change these
        )

    # -------- helpers for latest placement / dept / manager ----------
    def _latest_placement(self, emp: Employee) -> EmployeePlacement | None:
        if not emp:
            return None
        if hasattr(emp, "placements_cache") and emp.placements_cache:
            return emp.placements_cache[0]
        return (
            EmployeePlacement.objects.select_related(
                "company",
                "department", "department__manager",
                "sub_department", "sub_department__manager",
                "section", "section__manager",
                "sub_section", "sub_section__manager",
            )
            .filter(employee=emp)
            .order_by("-assigned_at")
            .first()
        )

    def _dept_and_manager(self, p: EmployeePlacement):
        if not p:
            return None, None, ""
        # derive top-down + org_path
        parts, dept_name, manager_name = [], None, None

        if p.department:
            parts.append(p.department.name)
            dept_name = p.department.name
            manager_name = getattr(p.department.manager, "name", None)

        if p.sub_department:
            parts.append(p.sub_department.name)
            dept_name = p.department.name  # top-level department stays same
            manager_name = getattr(p.sub_department.manager, "name", manager_name)

        if p.section:
            parts.append(p.section.name)
            manager_name = getattr(p.section.manager, "name", manager_name)

        if p.sub_section:
            parts.append(p.sub_section.name)
            manager_name = getattr(p.sub_section.manager, "name", manager_name)

        return dept_name, manager_name, " › ".join(parts)

    # -------- flat output, hide employment keys when absent ----------

   
    def _rep(self, field_name: str, value):
        if value is None:
            return None
        field = self.fields.get(field_name)
        return field.to_representation(value) if field else value
    
    def to_representation(self, instance: User):
        u = {
            "user_id": str(instance.user_id),
            "username": instance.username,
            "email": instance.email,
            "name": instance.name,
            "phone": instance.phone,
            "country_code": instance.country_code,
            "avatar": instance.avatar,
            "role": self._rep("role", instance.role),
            "position": instance.position,
            "gender": self._rep("gender", instance.gender),
            "is_default_password": getattr(instance, "is_default_password", False),
            "password_last_changed": getattr(instance, "password_last_changed", None),
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
        }

        emp: Employee | None = getattr(instance, "employee_profile", None)
        if not emp:
            return u  # no employment keys at all

        p = self._latest_placement(emp)
        dept_name, manager_name, org_path = self._dept_and_manager(p)

        u.update({
            "employee_id": str(emp.employee_id),
            "managerial_level": emp.managerial_level,
            "status": self._rep("status", emp.status),
            "employee_code": emp.employee_code,
            "job_type": self._rep("job_type", emp.job_type),
            "location": emp.location,
            "branch": self._rep("branch", emp.branch),
            "join_date": emp.join_date,
            "company_id": str(emp.company.company_id) if emp.company else None,
            "company_name": emp.company.name if emp.company else None,
            "department": dept_name,
            "direct_manager": manager_name,
            "org_path": org_path,
        })
        return u
     
   

    # -------- updates (no password here; role is read-only) ----------
    def update(self, instance: User, validated_data):
        # strip forbidden keys
        validated_data.pop("password", None)
        validated_data.pop("role", None)

        # split user vs employment updates
        user_updates = {k: v for k, v in validated_data.items() if k in USER_EDITABLE}
        emp_updates  = {k: v for k, v in validated_data.items() if k in EMP_EDITABLE}

        # update user
        for k, v in user_updates.items():
            setattr(instance, k, v)
        if user_updates:
            instance.save(update_fields=list(user_updates.keys()))

        # update employment (only if exists)
        if emp_updates:
            emp: Employee | None = getattr(instance, "employee_profile", None)
            if not emp:
                raise serializers.ValidationError(
                    {"employment": "No employment profile exists for this user."}
                )
            for k, v in emp_updates.items():
                setattr(emp, k, v)
            emp.save(update_fields=list(emp_updates.keys()))

        return instance
