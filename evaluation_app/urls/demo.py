from django.urls import path
from evaluation_app.views.htmx_demo import employee_list, employee_create

urlpatterns = [
    path("employees/",            employee_list,  name="emp-list"),
    path("employees/create/",     employee_create, name="emp-create"),
]
