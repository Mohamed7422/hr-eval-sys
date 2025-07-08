from rest_framework import serializers
from evaluation_app.models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Employee
        fields = "__all__"