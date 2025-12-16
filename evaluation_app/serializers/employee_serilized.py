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
    username          = serializers.CharField(source="user.username", read_only=True)
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
    #org_path   = serializers.SerializerMethodField()
    #direct_manager = serializers.SerializerMethodField()

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

    gender = LabelChoiceField(source="user.gender", choices=User._meta.get_field("gender").choices, required=False, read_only=True) 
    
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

    org_path = serializers.CharField(source="dept_path", read_only=True)
    direct_manager = serializers.CharField(source="direct_manager_name", read_only=True)
    

    class Meta:
        model  = Employee
        fields = [
             # primary key
            "employee_id",
            "employee_code",

            # flattened-position R/W
            "name", "username","email","phone","country_code","warnings","warnings_count","avatar","role","position",
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
        
        if obj.dept_path:
            return obj.dept_path.split(" › ")[0]
        return None
        # return the department of the first placement if any
       # p = self._latest_placement(obj)
        #return p.department.name if p and p.department else None
     
    
    def create(self, validated_data):
        user_payload = validated_data.pop("user", None)

        if isinstance(user_payload, User):
            # Case 1: attach to existing user
            user = user_payload

        elif isinstance(user_payload, dict):
            # Case 2: create a new User
            user_serializer = UserCreateSerializer(data=user_payload)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()  
            

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
