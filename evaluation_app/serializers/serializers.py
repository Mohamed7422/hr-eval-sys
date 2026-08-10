from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class EmailLoginSerializer(TokenObtainPairSerializer):
    """
    Override default claim payload:
    • Use email instead of username
    • Add role + full name for the front-end header
  
  Note: you can log int with username as default, but also you can use email but
    you need to ask for username as well.
    
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["name"] = user.name or user.email
        print(f"Token and email and name : {token}, {user.email}, {user.role}, {user.name}")
        return token
