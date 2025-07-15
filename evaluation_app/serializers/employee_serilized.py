from rest_framework import serializers
from evaluation_app.models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    class Meta:
        model  = Employee
        fields = "__all__"
        read_only_fields = ('employee_id',)