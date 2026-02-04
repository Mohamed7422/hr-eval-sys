from rest_framework import serializers
from evaluation_app.models import Company, Department
from django.contrib.auth import get_user_model



class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ("company_id", "created_at", "updated_at")


User = get_user_model()
class DepartmentSerializer(serializers.ModelSerializer):

     # allow clients to pass "manager": null or omit the field entirely
    manager = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())


    class Meta:
        model = Department
        fields = [
            "department_id",
            "name",
            "employee_count",
            "company",
            "manager",
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
          