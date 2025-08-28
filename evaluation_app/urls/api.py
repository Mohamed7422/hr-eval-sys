# evaluation_app/urls/api.py
from rest_framework.routers import DefaultRouter
from evaluation_app.views.employee import EmployeeViewSet
from evaluation_app.views.evaluationViewSet import EvaluationViewSet
from evaluation_app.views.auth import EmailLoginView 
from evaluation_app.views.objectiveViewSet import ObjectiveViewSet
from evaluation_app.views.competencyViewSet import CompetencyViewSet
from evaluation_app.views.weightsConfigurationViewSet import WeightConfigViewSet

from django.urls import path
from rest_framework_simplejwt.views import  (
           TokenRefreshView,    # POST /api/auth/refresh/
           TokenBlacklistView     # POST /api/auth/logout/ (requires blacklist app)
)

router = DefaultRouter()


#org

#router.register(r"employees", EmployeeViewSet)
router.register("employees", EmployeeViewSet, basename="employee") #GET /api/employees/  & GET /api/employees/{employee_id}/
router.register("evaluations", EvaluationViewSet, basename="evaluation") #GET /api/evaluations/  
router.register("objectives", ObjectiveViewSet, basename="objectives") #GET /api/objectives/    
router.register("competencies", CompetencyViewSet, basename="competency") #GET /api/competencies/
#GET /api/weights-configuration/ & GET /api/weights-configuration/{level_name}/
router.register("weights-configuration", WeightConfigViewSet, basename="weights-configuration") 

urlpatterns = [
    # JWT
    path("auth/login/",   EmailLoginView.as_view(),   name="jwt-login"),
    path("auth/refresh/", TokenRefreshView.as_view(),      name="jwt-refresh"),
    path("auth/logout/",  TokenBlacklistView.as_view(),    name="jwt-logout"),
    # REST resources   
    *router.urls
]          



 
