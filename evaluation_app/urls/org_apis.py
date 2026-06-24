from rest_framework.routers import DefaultRouter
from evaluation_app.views.orgViewSets import (
    CompanyViewSet, DepartmentViewSet, SubDepartmentViewSet, SectionViewSet, SubSectionViewSet, EmployeePlacementViewSet
)


router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")  # GET /api/org/companies/
router.register("departments", DepartmentViewSet, basename="department")  # GET  /api/org/departments/
router.register("sub-departments", SubDepartmentViewSet, basename="sub-departments") 
router.register("sections", SectionViewSet, basename="sections")
router.register("sub-sections", SubSectionViewSet, basename="sub-sections") # GET /api/org/sub-sections/
router.register("placements", EmployeePlacementViewSet, basename="placements")# GET /api/org/placements/

urlpatterns = router.urls
