from rest_framework import serializers
from evaluation_app.models import Objective, ObjectiveState, Evaluation
from evaluation_app.services.objective_math import compute_objective_score
from evaluation_app.utils import LabelChoiceField
from django.core.exceptions import ValidationError as DjangoValidationError
from evaluation_app.services.objective_math import validate_single_objective_weight, validate_objectives_constraints


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
    weight         = serializers.FloatField(required=True,min_value = 10.0,
                                            max_value = 40.0, allow_null=False,
                                            help_text="Objective weight (10-40%), all weights must sum to 100%")
    status         = LabelChoiceField(choices=ObjectiveState.choices)
    created_at     = serializers.DateTimeField(read_only=True)
    updated_at     = serializers.DateTimeField(read_only=True)

    score = serializers.SerializerMethodField(read_only=True)


    class Meta:
        model  = Objective
        fields = [
            "objective_id",
            "evaluation_id",
            "employee_id",
            "title",
            "description",
            "score",
            "target",
            "achieved",
            "weight",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("objective_id", "created_at", "updated_at", "score")

    def validate_weight(self, value):
        """
        Validate that weight is within 10-40% range.
        """
        if value is None:
            raise serializers.ValidationError("Weight is required")
        
        try:
            validate_single_objective_weight(float(value))
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        
        return value
    def validate_target(self, value):
        """
        Validate that target is positive.
        """
        if value is not None and value <= 0:
            raise serializers.ValidationError("Target must be greater than 0, specifically 10")
        return value
  
    def validate_achieved(self, value):
        """
        Validate that achieved is non-negative.
        """
        if value is not None and value < 0:
            raise serializers.ValidationError("Achieved value cannot be negative")
        return value
    def get_score(self, obj):
        return compute_objective_score(obj, cap_at_100=True)

class ObjectiveBulkValidationSerializer(serializers.Serializer):
    """
    Serializer for validating all objectives of an evaluation together.
    Used to check that total weights sum to 100% and count is 4-6.
    """
    evaluation_id = serializers.UUIDField()

    def validate(self, attrs):
        evaluation_id = attrs.get('evaluation_id')
        
        try:
            evaluation = Evaluation.objects.get(evaluation_id=evaluation_id)
        except Evaluation.DoesNotExist:
            raise serializers.ValidationError({"evaluation_id": "Evaluation not found"})
        
        # Validate all constraints
        try:
            validate_objectives_constraints(evaluation)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"objectives": str(e)})
        
        return attrs    
       
