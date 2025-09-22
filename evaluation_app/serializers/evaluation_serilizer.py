from rest_framework import serializers
from django.contrib.auth import get_user_model
from evaluation_app.models import (
    Evaluation, Objective, Competency, EmpStatus, EvalStatus, EvalType
)
from evaluation_app.serializers.employee_serilized import EmployeeSerializer
from evaluation_app.models import Employee
from evaluation_app.utils import LabelChoiceField
from evaluation_app.serializers.objective_serializer import ObjectiveSerializer
from evaluation_app.serializers.competency_serializer import CompetencySerializer
from evaluation_app.services.objective_math import calculate_objectives_score
from evaluation_app.services.competency_math import calculate_competencies_score

User = get_user_model()

 
class EvaluationSerializer(serializers.ModelSerializer):

    #--WRITE-ONLY--

    employee_id = serializers.PrimaryKeyRelatedField(
        source="employee",
        queryset=Employee.objects.all(),
    )

    reviewer_id = serializers.PrimaryKeyRelatedField(
        source="reviewer",
        queryset=User.objects.all(),
        allow_null=True,
        required=False
    )

    """
    • Nested objectives (read-only list).  
    • Employee & reviewer use UUIDs but return brief info.
    """
    employee     = serializers.CharField(
        source="employee.user.name", read_only=True)
    reviewer     = serializers.CharField(
        source="reviewer.name", read_only=True, default=None
    )
    objectives   = ObjectiveSerializer(source="objective_set",many=True, read_only=True)
    competencies = CompetencySerializer(source="competency_set",many=True, read_only=True)
    type         = LabelChoiceField(choices=EvalType.choices)
    status       = LabelChoiceField(choices=EvalStatus.choices)
    score        = serializers.DecimalField(max_digits=4, decimal_places=2, 
                                            allow_null=True, required=False)
    
    created_at   = serializers.DateTimeField(read_only=True)
    updated_at   = serializers.DateTimeField(read_only=True)

    objectives_score = serializers.SerializerMethodField(read_only=True)
    competencies_score = serializers.SerializerMethodField(read_only=True) 
    class Meta:
        model = Evaluation
        fields = [
            "evaluation_id", 
            "employee", "employee_id",
            "type", "status", "score",
            "reviewer", "reviewer_id",
            "period",
            "created_at", "updated_at",
            "objectives_score",
            "competencies_score",
            "objectives",
            "competencies"
        ]
        read_only_fields = ("evaluation_id", "created_at", "updated_at")

     # ── create / update helpers ──────────────────────────
    def create(self, validated_data):
        return super().create(validated_data)  
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
    
    def get_objectives_score(self, obj):
        return calculate_objectives_score(obj, cap_at_100=True, return_breakdown=False)
    
    def get_competencies_score(self, obj):
        return calculate_competencies_score(obj, cap_at_100=True)    