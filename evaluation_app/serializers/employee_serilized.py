# evaluation_app/serializers/employee_serializer.py

from rest_framework import serializers
from evaluation_app.models import Employee, Department, Company, ManagerialLevel,EmpStatus
from accounts.models import User
from accounts.serializers.user_serializer import UserCreateSerializer
from evaluation_app.serializers.org_serializers import CompanySerializer, DepartmentSerializer
from evaluation_app.utils import LabelChoiceField
class EmployeeSerializer(serializers.ModelSerializer):
    # READ: show full user data
    #user = UserCreateSerializer(read_only=True)
     # ─────── READ‑ONLY FLATTENED USER FIELDS ─────────────────────
    name              = serializers.CharField(source="user.name",           read_only=True)
    email             = serializers.CharField(source="user.email",          read_only=True)
    phone             = serializers.CharField(source="user.phone",          read_only=True)
    avatar            = serializers.CharField(source="user.avatar", allow_blank=True, read_only=True)
    role              = LabelChoiceField(source="user.role", 
                                         choices=User._meta.get_field("role").choices,
                                         required=False)
    position          = serializers.CharField(source="user.title",          read_only=True)

     # ─────── CHOICE DISPLAY & RELATED FIELDS ───────────────────────
    managerial_level = LabelChoiceField(choices=ManagerialLevel.choices)
    status            = LabelChoiceField(choices=EmpStatus.choices)

    company_name      = serializers.CharField(source="company.name", read_only=True)
    department      = serializers.SlugRelatedField(source="departments", many=True, slug_field="name", read_only=True)
     # ─────── TIMESTAMPS / DATES ────────────────────────────────────
    join_date         = serializers.DateField(format="%Y-%m-%d")
    created_at        = serializers.DateTimeField(format="iso‑8601",          read_only=True)
    updated_at        = serializers.DateTimeField(format="iso‑8601",          read_only=True)

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

            # read‑only flattened
            "name","email","phone","avatar","role","position",
            "managerial_level","status",

            "company_name","department",
            "join_date","created_at","updated_at",

            # write‑only
            "user_id","user_data",
            "company_id",
            "departments_ids",
        ]
        read_only_fields = ("employee_id",)

    #def get_department(self, obj):
       #     name = obj.departments.all().values_list("name", flat=True)
       #     return ", ".join(name) # e.g. "Dev, QA, HR"
        

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
        # 1) nested user update?
        user_payload = validated_data.pop("user", None)
        if user_payload:
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
