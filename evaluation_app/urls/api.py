# evaluation_app/urls/api.py
from rest_framework.routers import DefaultRouter
from evaluation_app.views.employee import EmployeeViewSet

router = DefaultRouter()
router.register(r"employees", EmployeeViewSet)

urlpatterns = router.urls
