from rest_framework import serializers
from evaluation_app.models import Company, Department,CompanySize,Employee, EmployeePlacement, SubDepartment, Section, SubSection
from django.contrib.auth import get_user_model
from evaluation_app.utils import LabelChoiceField


class CompanySerializer(serializers.ModelSerializer):
    # ─────── CHOICE DISPLAY & RELATED FIELDS ───────────────────────
    size= LabelChoiceField(choices=CompanySize.choices)

    class Meta:
        model = Company
        fields = [
            "company_id", "name", "address", "industry", "size", "created_at", "updated_at"
            ]
        read_only_fields = ("company_id", "created_at", "updated_at")

#
User = get_user_model()
class DepartmentSerializer(serializers.ModelSerializer):

     # allow clients to pass "manager": null or omit the field entirely
    manager = serializers.CharField(source="manager.name", allow_null=True, required=False)
    company = serializers.CharField(source="company.name", read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(source="company",
                                                   queryset=Company.objects.all(),
                                                   write_only=True)
    manager_id = serializers.PrimaryKeyRelatedField(source="manager",
                                                   queryset=User.objects.all(),
                                                   write_only=True,
                                                   allow_null=True,
                                                   required=False)
    employee_count = serializers.IntegerField(required=False,default=0)
    

    class Meta:
        model = Department
        fields = [
            "department_id",
            "name",
            "employee_count",
            "company",
            "manager",
            "company_id",
            "manager_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("department_id", "created_at", "updated_at")
 
class SubDepartmentSerializer(serializers.ModelSerializer):
    department_id = serializers.PrimaryKeyRelatedField(source="department", queryset=Department.objects.all())
    department    = serializers.CharField(source="department.name", read_only=True)
    manager_id    = serializers.PrimaryKeyRelatedField(source="manager", queryset=User.objects.all(), allow_null=True, required=False)
    manager       = serializers.CharField(source="manager.name", read_only=True)
    

    class Meta:
        model  = SubDepartment
        fields = ["sub_department_id", "name", "employee_count", "department", "department_id",
                  "manager", "manager_id", "created_at", "updated_at"]
        read_only_fields = ("sub_department_id","created_at","updated_at")


class SectionSerializer(serializers.ModelSerializer):
    sub_department_id = serializers.PrimaryKeyRelatedField(source="sub_department", queryset=SubDepartment.objects.all(), write_only=True)
    sub_department    = serializers.CharField(source="sub_department.name", read_only=True)
    manager_id        = serializers.PrimaryKeyRelatedField(source="manager", queryset=User.objects.all(), allow_null=True, required=False)
    manager           = serializers.CharField(source="manager.name", read_only=True)
    department_id     = serializers.PrimaryKeyRelatedField(source="sub_department.department",  read_only=True)
    class Meta:
        model  = Section
        fields = ["section_id", "name", "employee_count", "department_id", "sub_department", "sub_department_id",
                  "manager", "manager_id", "created_at", "updated_at"]
        read_only_fields = ("section_id","created_at","updated_at")


class SubSectionSerializer(serializers.ModelSerializer):
    section_id = serializers.PrimaryKeyRelatedField(source="section", queryset=Section.objects.all(), write_only=True )
    section    = serializers.CharField(source="section.name", read_only=True)
    manager_id = serializers.PrimaryKeyRelatedField(source="manager", queryset=User.objects.all(), allow_null=True, required=False)
    manager    = serializers.CharField(source="manager.name", read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(source="section.sub_department.department", read_only=True)
    class Meta:
        model  = SubSection
        fields = ["sub_section_id", "name", "employee_count", "department_id", "section", "section_id",
                  "manager", "manager_id", "created_at", "updated_at"]
        read_only_fields = ("sub_section_id","created_at","updated_at")


class EmployeePlacementSerializer(serializers.ModelSerializer):
    # Write
    employee_id       = serializers.PrimaryKeyRelatedField(
        source="employee", queryset=Employee.objects.all(),required=False
    )
    
    department_id     = serializers.PrimaryKeyRelatedField(
        source="department", queryset=Department.objects.all(),
        required=False, allow_null=True
    )
    sub_department_id = serializers.PrimaryKeyRelatedField(
        source="sub_department", queryset=SubDepartment.objects.all(),
        required=False, allow_null=True
    )
    section_id        = serializers.PrimaryKeyRelatedField(
        source="section", queryset=Section.objects.all(),
        required=False, allow_null=True
    )
    sub_section_id    = serializers.PrimaryKeyRelatedField(
        source="sub_section", queryset=SubSection.objects.all(),
        required=False, allow_null=True
    )

    # Read-only niceties
    employee_name       = serializers.CharField(source="employee.user.name", read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(source="company", read_only=True)
    company_name        = serializers.CharField(source="company.name", read_only=True)
    department_name     = serializers.CharField(source="department.name", read_only=True)
    sub_department_name = serializers.CharField(source="sub_department.name", read_only=True)
    section_name        = serializers.CharField(source="section.name", read_only=True)
    sub_section_name    = serializers.CharField(source="sub_section.name", read_only=True)
   
    class Meta:
        model  = EmployeePlacement
        fields = [
            "placement_id",
            "employee_id", "employee_name",
            # company_id REMOVED from API surface
            "company_id",
            "company_name",
            "department_id", "department_name",
            "sub_department_id", "sub_department_name",
            "section_id", "section_name",
            "sub_section_id", "sub_section_name",
            "assigned_at",
        ]
        read_only_fields = (
            "placement_id", "assigned_at",
            "employee_name", "company_name",
            "department_name", "sub_department_name", "section_name", "sub_section_name",
        )
        validators = []  # disable the default unique_together validator
    
    # --- helpers ---
    def _coerce_blanks(self, attrs):
        for k in ("department", "sub_department", "section", "sub_section"):
            if k in attrs and attrs[k] == "":
                attrs[k] = None
    # ----- lineage normalization helpers -----
    def _normalize_lineage(self, attrs):
        self._coerce_blanks(attrs)

        dep  = attrs.get("department")
        sdep = attrs.get("sub_department")
        sec  = attrs.get("section")
        ssec = attrs.get("sub_section")

        # deepest -> parent
        if ssec:
            sec_from_ssec  = ssec.section
            sdep_from_sec  = sec_from_ssec.sub_department if sec_from_ssec else None
            dep_from_sdep  = sdep_from_sec.department     if sdep_from_sec else None
            if sec and sec != sec_from_ssec:
                raise serializers.ValidationError("sub_section_id does not belong to the provided section_id.")
            sec  = sec or sec_from_ssec
            if sdep and sdep != sdep_from_sec:
                raise serializers.ValidationError("sub_section/section do not belong to the provided sub_department_id.")
            sdep = sdep or sdep_from_sec
            if dep and dep != dep_from_sdep:
                raise serializers.ValidationError("sub_section lineage does not match the provided department_id.")
            dep  = dep or dep_from_sdep

        if sec:
            sdep_from_sec = sec.sub_department
            dep_from_sdep = sdep_from_sec.department if sdep_from_sec else None
            if sdep and sdep != sdep_from_sec:
                raise serializers.ValidationError("section_id does not belong to the provided sub_department_id.")
            sdep = sdep or sdep_from_sec
            if dep and dep != dep_from_sdep:
                raise serializers.ValidationError("section lineage does not match the provided department_id.")
            dep  = dep or dep_from_sdep

        if sdep:
            dep_from_sdep = sdep.department
            if dep and dep != dep_from_sdep:
                raise serializers.ValidationError("sub_department_id does not belong to the provided department_id.")
            dep = dep or dep_from_sdep

        return dep, sdep, sec, ssec
    
    def validate(self, attrs):
        
        employee = attrs.get("employee") or getattr(self.instance, "employee", None)
        if not employee:
            raise serializers.ValidationError("employee_id is required.")

        dep, sdep, sec, ssec = self._normalize_lineage(attrs)

        company = employee.company
        if not company:
            raise serializers.ValidationError("Employee has no company set; cannot place.")

        # company consistency check
        def unit_company(u):
            if u is None: return None
            if hasattr(u, "company"): return u.company                    # department
            if hasattr(u, "department"): return u.department.company      # sub_department
            if hasattr(u, "sub_department"): return u.sub_department.department.company  # section
            if hasattr(u, "section"): return u.section.sub_department.department.company # sub_section
            return None

        for unit, label in [(dep, "department"), (sdep, "sub_department"), (sec, "section"), (ssec, "sub_section")]:
            uc = unit_company(unit)
            if uc and uc != company:
                raise serializers.ValidationError(f"{label} belongs to a different company than the employee.")

        attrs["department"]     = dep
        attrs["sub_department"] = sdep
        attrs["section"]        = sec
        attrs["sub_section"]    = ssec
        attrs["company"]        = company
        return attrs

    # one row per employee (upsert)
    def create(self, validated_data):
        employee = validated_data["employee"]
        placement, created = EmployeePlacement.objects.get_or_create(
            employee=employee,
            defaults={
                "company":        validated_data["company"],
                "department":     validated_data.get("department"),
                "sub_department": validated_data.get("sub_department"),
                "section":        validated_data.get("section"),
                "sub_section":    validated_data.get("sub_section"),
            },
        )
        if not created:
            for f in ("company","department","sub_department","section","sub_section"):
                if f in validated_data:
                    setattr(placement, f, validated_data.get(f))
            placement.save()
        return placement

    def update(self, instance, validated_data):
        for f in ("department","sub_department","section","sub_section"):
            if f in validated_data:
                setattr(instance, f, validated_data.get(f))
        instance.company = instance.employee.company
        instance.save()
        return instance
 

 