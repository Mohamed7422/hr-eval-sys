from rest_framework_simplejwt.views import TokenObtainPairView
from evaluation_app.serializers.serializers import EmailLoginSerializer

class EmailLoginView(TokenObtainPairView):
    serializer_class = EmailLoginSerializer