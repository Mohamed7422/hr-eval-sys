from rest_framework import serializers
from evaluation_app.models import Objective, ObjectiveState, Evaluation
from evaluation_app.utils import LabelChoiceField
 
    


class ObjectiveSerializer(serializers.ModelSerializer):
    objective_id   = serializers.UUIDField(read_only=True)
    evaluation_id  = serializers.PrimaryKeyRelatedField(
        source="evaluation",
        queryset=Evaluation.objects.all()
    )
     
    employee_id = serializers.UUIDField(
        source="evaluation.employee.employee_id",
        read_only=True
    )
    title          = serializers.CharField()
    description    = serializers.CharField(allow_blank=True, required=False)
    target         = serializers.FloatField(allow_null=True, required=False)
    achieved       = serializers.FloatField(allow_null=True, required=False)
    weight         = serializers.FloatField()
    status         = LabelChoiceField(choices=ObjectiveState.choices)
    created_at     = serializers.DateTimeField(read_only=True)
    updated_at     = serializers.DateTimeField(read_only=True)

    class Meta:
        model  = Objective
        fields = [
            "objective_id",
            "evaluation_id",
            "employee_id",
            "title",
            "description",
            "target",
            "achieved",
            "weight",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("objective_id", "created_at", "updated_at")
