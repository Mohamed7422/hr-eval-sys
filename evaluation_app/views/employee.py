from rest_framework import viewsets
from evaluation_app.models import Employee
from evaluation_app.serializers.employee import EmployeeSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer