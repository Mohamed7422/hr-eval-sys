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

   # def create(self, data):
   #     company = data.pop("company")
   #     manager_id = data.pop('manager_id', None)
    #    cid = company.company_id
    #    return Department.objects.create(
     #       company_id=cid
     #       manager_id=manager_id
      #      **data
      #  )
    
  #  def update(self, instance, data):
  #      for f in ("name", "employee_count"):
  #          if f in data:
  #               setattr(instance, f, data[f])
  #      if "manager_id" in data:
  #          instance.manager_id = data["manager_id"]
  #      instance.save()
  #      return instance  
  
class SubDepartmentSerializer(serializers.ModelSerializer):
    department_id = serializers.PrimaryKeyRelatedField(source="department", queryset=Department.objects.all(), write_only=True)
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

    class Meta:
        model  = Section
        fields = ["section_id", "name", "employee_count", "sub_department", "sub_department_id",
                  "manager", "manager_id", "created_at", "updated_at"]
        read_only_fields = ("section_id","created_at","updated_at")


class SubSectionSerializer(serializers.ModelSerializer):
    section_id = serializers.PrimaryKeyRelatedField(source="section", queryset=Section.objects.all(), write_only=True )
    section    = serializers.CharField(source="section.name", read_only=True)
    manager_id = serializers.PrimaryKeyRelatedField(source="manager", queryset=User.objects.all(), allow_null=True, required=False)
    manager    = serializers.CharField(source="manager.name", read_only=True)

    class Meta:
        model  = SubSection
        fields = ["sub_section_id", "name", "employee_count", "section", "section_id",
                  "manager", "manager_id", "created_at", "updated_at"]
        read_only_fields = ("sub_section_id","created_at","updated_at")


class EmployeePlacementSerializer(serializers.ModelSerializer):
    
    employee_id       = serializers.PrimaryKeyRelatedField(source="employee",
                                                            queryset=Employee.objects.all())
    company_id        = serializers.PrimaryKeyRelatedField(source="company", queryset=Company.objects.all())
    department_id     = serializers.PrimaryKeyRelatedField(source="department", queryset=Department.objects.all(), required=False, allow_null=True)
    sub_department_id = serializers.PrimaryKeyRelatedField(source="sub_department", queryset=SubDepartment.objects.all(), required=False, allow_null=True)
    section_id        = serializers.PrimaryKeyRelatedField(source="section", queryset=Section.objects.all(), required=False, allow_null=True)
    sub_section_id    = serializers.PrimaryKeyRelatedField(source="sub_section", queryset=SubSection.objects.all(), required=False, allow_null=True)

    employee_name = serializers.CharField(source="employee.user.name", read_only=True)
    company_name  = serializers.CharField(source="company.name", read_only=True)
    department_name= serializers.CharField(source="department.name", read_only=True)
    sub_department_name = serializers.CharField(source="sub_department.name", read_only=True)
    section_name   = serializers.CharField(source="section.name", read_only=True)
    sub_section_name= serializers.CharField(source="sub_section.name", read_only=True)
    
    class Meta:
        model  = EmployeePlacement
        fields = ["placement_id","employee_id","employee_name","company_id","company_name",
                  "department_id","department_name","sub_department_id","sub_department_name",
                  "section_id","section_name","sub_section_id","sub_section_name","assigned_at"]
        read_only_fields = ("placement_id","assigned_at","employee_name",
                            "company_name","department_name","sub_department_name",
                            "section_name","sub_section_name")
        validators=[]
    
    def validate(self, attrs):
        # Remove the if self.instance check - validate for both create and update
         
        employee = attrs.get("employee")
        company  = attrs.get("company")
        
        if employee and company:
            if employee.company != company:
                raise serializers.ValidationError({
                    "error": f"Employee {employee.employee_id} does not belong to company {company.company_id}"
                })
        
        # exactly one target level must be chosen
        level_keys = ["department", "sub_department", "section", "sub_section"]
        chosen = [k for k in level_keys if attrs.get(k)]
        if len(chosen) != 1:
            raise serializers.ValidationError(
                "Exactly one of department_id / sub_department_id / section_id / sub_section_id must be provided."
            )
        
        return attrs
    def create(self, validated_data):
        # Create with ALL fields at once to satisfy the constraint
        create_data = {
            'employee': validated_data['employee'],
            'company': validated_data['company'],
        }
        
        # Add the single location field that was provided
        locations = ['department', 'sub_department', 'section', 'sub_section']
        for location in locations:
            if location in validated_data:
                create_data[location] = validated_data[location]
                break
        
        # Create with all required fields in one atomic operation
        placement = EmployeePlacement.objects.create(**create_data)
        return placement