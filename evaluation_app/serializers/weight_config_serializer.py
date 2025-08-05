from rest_framework import serializers
from evaluation_app.models import WeightsConfiguration, ManagerialLevel
from evaluation_app.utils import LabelChoiceField

class WeightConfigSerializer(serializers.ModelSerializer):
    level_name = LabelChoiceField(choices=ManagerialLevel.choices, read_only=True)

    class Meta:
        model = WeightsConfiguration
        fields= [
            'level_name',
            'core_weight',
            'leadership_weight',
            'functional_weight',
            'competency_weight',
            'objective_weight'
        ]
        read_only_fields = ('level_name',)