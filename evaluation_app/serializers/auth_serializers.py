# evaluation_app/serializers/auth_serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class EmailLoginSerializer(TokenObtainPairSerializer):
    """
    Supports:
    1) email + password
    2) username + password
    3) email + username + password (both must match)
    """
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SimpleJWT auto-adds a required field named self.username_field (usually "username")
        # Relax it so email-only logins don't error.
        if self.username_field in self.fields:
            self.fields[self.username_field].required = False
            self.fields[self.username_field].allow_blank = True


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

    def validate(self, attrs):
        username = attrs.get("username") or None
        email = attrs.get("email") or None
        password = attrs.get("password")
        
        if not (username or email):
            raise serializers.ValidationError("Provide username or email.")

         
        user = authenticate(
            request=self.context.get("request"),
            username=username,  
            email=email,      
            password=password,
        )
        if not user:
            raise serializers.ValidationError("Invalid credentials.")

         
        if username and email and (user.username != username or user.email.lower() != email.lower()):
            raise serializers.ValidationError("Email and username do not match.")
        
         # Get role display value after user is authenticated
        from accounts.models import Role
        role = getattr(user, "role", None)
        role_display = dict(Role.choices)[role] if role else None

        # Build tokens manually 
        refresh = RefreshToken.for_user(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": role_display,
            "name": getattr(user, "name", None) or user.email or user.username,
            "is_default_password": getattr(user, "is_default_password", False),
        }
        self.user = user 
        return data
