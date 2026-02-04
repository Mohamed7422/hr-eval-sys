from rest_framework import serializers
from evaluation_app.models import (
    Evaluation, Objective, Competency, EmpStatus, EvalStatus, EvalType
)
from evaluation_app.serializers.employee_serilized import EmployeeSerializer


class ObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Objective
        fields = "__all__"
        read_only_fields = ("objective_id", "created_at", "updated_at")

class EvaluationSerializer(serializers.ModelSerializer):
    """
    • Nested objectives (read-only list).  
    • Employee & reviewer use UUIDs but return brief info.
    """
    employee = EmployeeSerializer(read_only=True)
    employee_id = serializers.UUIDField()
    reviewer_id = serializers.UUIDField()
    objectives  = ObjectiveSerializer(many=True)
    class Meta:
        model = Evaluation
        fields = [
            "evaluation_id", "employee", "employee_id",
            "type", "status", "score",
            "reviewer_id", "period",
            "created_at", "updated_at",
            "objectives",
        ]
        read_only_fields = ("evaluation_id", "created_at", "updated_at")

     # ── create / update helpers ──────────────────────────
    def create(self, validated_data):
        print(">> Received validated_data:", validated_data)
        employee_id = validated_data.pop('employee_id')  
        reviewer_id = validated_data.pop('reviewer_id', None) 

        employee = self.context['request'].user.employee_profile.__class__.objects.get(
            pk=employee_id
        )
        reviewer = None
        if reviewer_id: 
            from accounts.models import User
            reviewer = User.objects.get(pk=reviewer_id)

        return Evaluation.objects.create(
            employee=employee,
            reviewer=reviewer,
            **validated_data
        ) 
    
    def update(self, instance, validated_data):
     
     # Handle objectives update if present
     if 'objectives' in validated_data:
        objectives_data = validated_data.pop('objectives')
        
        for objective_data in objectives_data:
            # If objective has ID, update existing
            if 'objective_id' in objective_data:
                objective = instance.objectives.filter(
                    objective_id=objective_data['objective_id']
                ).first()
                if objective:
                    for attr, value in objective_data.items():
                        setattr(objective, attr, value)
                    objective.save()
            # If no ID, create new objective
            else:
                Objective.objects.create(
                    evaluation=instance,
                    **objective_data
                )

    # Handle other fields as before
     for field in ("status", "score", "reviewer_id"):
        if field in validated_data:
            setattr(instance, field, validated_data[field])
    
     instance.save()
     return instance