# evaluation_app/views/objective_viewset.py
from rest_framework import viewsets
from evaluation_app.serializers.evaluation_serilizer import ObjectiveSerializer
from evaluation_app.models import Objective
from evaluation_app.permissions import IsAdmin, IsHR, IsHOD, IsLineManager

class ObjectiveViewSet(viewsets.ModelViewSet):
    queryset = Objective.objects.select_related("evaluation")
    serializer_class = ObjectiveSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return []  # anyone who can access the evaluation already sees objectives
        # create/update/delete
        return [IsAdmin() | IsHR() | IsHOD() | IsLineManager()]
