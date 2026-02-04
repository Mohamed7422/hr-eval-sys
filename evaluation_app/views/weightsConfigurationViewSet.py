from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from evaluation_app.models import WeightsConfiguration
from evaluation_app.serializers.weight_config_serializer import WeightConfigSerializer
from evaluation_app.permissions import IsAdmin, IsHR

class WeightConfigViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, viewsets.GenericViewSet
    ):
    """
    • GET  /weights-configuration/       → list all levels  
    • GET  /weights-configuration/{level_name}/ → retrieve one  
    • PUT  /weights-configuration/{level_name}/ → update weights for that level
    """


    queryset = WeightsConfiguration.objects.all()
    serializer_class = WeightConfigSerializer
    lookup_field = "level_name"
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        #only Admin or HR can update weights, anyone authenticated may list/retrieve
        if self.action in ("update", "partial_update"):
            return [(IsAdmin | IsHR)()]
        return super().get_permissions()    