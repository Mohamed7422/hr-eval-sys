from rest_framework import serializers
from evaluation_app.models import Company, Department,CompanySize
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
          