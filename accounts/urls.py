from django.urls import path
from .views import UserCreateAPIView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"users", UserCreateAPIView, basename="user")

urlpatterns = router.urls