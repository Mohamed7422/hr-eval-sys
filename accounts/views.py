from accounts.serializers.user_serializer import UserCreateSerializer
from django.contrib.auth import get_user_model
from evaluation_app.permissions import IsAdmin, IsHR, IsSelfOrAdminHR 
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from accounts.serializers.password_change_serializer import PasswordChangeSerializer
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework.decorators import action
User = get_user_model()

class UserCreateAPIView(viewsets.ModelViewSet):
    serializer_class = UserCreateSerializer

    # queryset not needed for create-only but DRF wants it:
    queryset = User.objects.all()
    search_fields = ["username", "email", "first_name", "last_name"]
    lookup_field = "user_id"  # use UUID for lookups

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [(IsHR | IsAdmin)()]
        if self.action in ("update", "partial_update"):
            if self.request.user.role in  ("ADMIN", "HR"):
                return [(IsAdmin | IsHR)()]
            else:
               return [IsSelfOrAdminHR()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ("ADMIN", "HR"):
            return User.objects.all()
        return User.objects.filter(user_id=user.user_id)
        

    
    #--------------------------------------------   
    @action(
            detail=False,
            methods=["post"],
            url_path="change-password",
            permission_classes=[IsAuthenticated],
    )
    def change_password(self, request):
        user = request.user
        serializers =  PasswordChangeSerializer(
            data = request.data,
            context = {'request': request}
        )

        if serializers.is_valid():
            if not user.check_password(serializers.validated_data['old_password']): 
                return Response(
                    {"old_password": "Wrong password"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializers.validated_data['new_password'])

            user.is_default_password = False
            user.password_last_changed = timezone.now()
            user.save()

            response_data= {
                "status": "success",
                "message": "Password changed successfully",
                "is_default_password": False
            }

            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)

            
