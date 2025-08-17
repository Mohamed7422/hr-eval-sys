# evaluation_app/serializers/competency_serializer.py

from rest_framework import serializers
from evaluation_app.models import Competency, Evaluation, CompetencyCategory
from evaluation_app.utils import LabelChoiceField

class CompetencySerializer(serializers.ModelSerializer):
    competence_id   = serializers.UUIDField(read_only=True)

    # Clients POST / PATCH with an `evaluation_id`; we write into .evaluation
    evaluation_id = serializers.PrimaryKeyRelatedField(
        source="evaluation",
        queryset=Evaluation.objects.all()
    )

    # We expose employee_id read-only, pulled from the linked evaluation
    employee_id = serializers.UUIDField(
        source="evaluation.employee.employee_id",
        read_only=True
    )

    name           = serializers.CharField()
    category       = LabelChoiceField(choices=CompetencyCategory.choices)
    required_level = serializers.FloatField()
    actual_level   = serializers.FloatField()
    weight         = serializers.FloatField()
    description    = serializers.CharField(allow_blank=True, required=False)

    created_at     = serializers.DateTimeField(read_only=True)
    updated_at     = serializers.DateTimeField(read_only=True)

    class Meta:
        model  = Competency
        fields = [
            "competence_id",
            "evaluation_id",
            "employee_id",
            "name",
            "category",
            "required_level",
            "actual_level",
            "weight",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("competence_id", "created_at", "updated_at")
