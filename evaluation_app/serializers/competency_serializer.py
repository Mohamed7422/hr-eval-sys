# evaluation_app/serializers/competency_serializer.py

from rest_framework import serializers
from evaluation_app.models import Competency, Evaluation, CompetencyCategory
from evaluation_app.utils import LabelChoiceField
from evaluation_app.services.competency_math import competency_score

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
    weight         = serializers.FloatField(read_only=True, required=False)
    score = serializers.SerializerMethodField(read_only=True)
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
            "score",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("competence_id", "created_at", "updated_at")


    def get_score(self, obj:Competency) -> float:
        return competency_score(obj, cap_at_100=True)    
