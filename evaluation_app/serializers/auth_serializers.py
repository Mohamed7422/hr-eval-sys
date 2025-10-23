# evaluation_app/serializers/auth_serializers.py
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class EmailLoginSerializer(TokenObtainPairSerializer):
    """
    Supports:
    1) email + password
    2) username + password
    3) email + username + password (both must match)
    """
    

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        role = getattr(user, "role", None)
        if role:
            from accounts.models import Role
            token["role"] = dict(Role.choices)[role]
       
        token["name"] = getattr(user, "name", None) or user.email or user.username
        token["is_default_password"] = getattr(user, "is_default_password", False)
        return token

    