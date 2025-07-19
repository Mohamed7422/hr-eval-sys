from rest_framework import serializers
from evaluation_app.models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField()
    # name = serializers.CharField(source='user.name', read_only=True)
    # email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model  = Employee
        fields = [
            "employee_id", "user_id", "company", "departments",
            "managerial_level", "status", "join_date",
        ] #
        read_only_fields = ('employee_id',)
        

    def create(self, validated_data):
        # Extract user_id from validated_data
        user_id = validated_data.pop('user_id')
        from accounts.models import User # local import to avoid circular dependency
        user = User.objects.get(pk=user_id)
        
        # Create Employee instance
        employee = Employee.objects.create(user=user, **validated_data)
        return employee    