"""
URL configuration for hr_evaluation project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.generic import TemplateView
from evaluation_app.views.profileView import MyProfileView

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema")),
    path('admin/', admin.site.urls),
    path("api/", include("evaluation_app.urls.api")),
    path("", TemplateView.as_view(template_name="welcome.html"), name="home"),
    path("api/org/", include("evaluation_app.urls.org_apis")),
    path("api/accounts/", include("accounts.urls")),
    path("api/my-profile/", MyProfileView.as_view(), name="my-profile"),
]
