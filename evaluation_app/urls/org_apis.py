from rest_framework.routers import DefaultRouter
from evaluation_app.views.orgViewSets import (
    CompanyViewSet, DepartmentViewSet )




router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")  # GET /api/org/companies/
router.register("departments", DepartmentViewSet, basename="department")  # GET  /api/org/departments/

urlpatterns = router.urls
