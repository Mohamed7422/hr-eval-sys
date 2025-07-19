from django.shortcuts import render
from rest_framework import generics, permissions
from accounts.serializers.user_serializer import UserCreateSerializer
from django.contrib.auth import get_user_model
from evaluation_app.permissions import IsAdmin, IsHR
from rest_framework import viewsets, filters

User = get_user_model()

# Create your views here.

class UserCreateAPIView(viewsets.ModelViewSet):
    serializer_class = UserCreateSerializer

    # queryset not needed for create-only but DRF wants it:
    queryset = User.objects.all()
    search_fields = ["username", "email", "first_name", "last_name"]
    lookup_field = "user_id"  # use UUID for lookups

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [(IsHR | IsAdmin)()]
        if self.action in ("list", "retrieve"):
            return [(IsHR | IsAdmin)()]
        return [permissions.IsAuthenticated()]
        
