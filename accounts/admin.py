from django.contrib import admin
from django.conf import settings
from django.apps import apps
from .models import User, Role
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Register your models here.
# ───────────────────────────────
#  User
# ───────────────────────────────
# User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
# Role = apps.get_model("accounts", "Role")

@admin.register(User)
class UserAdmin(BaseUserAdmin):
     list_display = ("username", "email", "role","country_code", "is_staff", "date_joined")
     list_filter  = ("role", "is_staff", "is_superuser", "is_active", "groups")
     search_fields = ("username", "email", "first_name", "last_name", "phone","country_code")
     ordering = ("-date_joined",)
     fieldsets = (
            (None, {"fields": ("username", "email", "password")}),
            ("Personal info", {"fields": ("first_name", "last_name","name", "phone","country_code", "avatar", "title")}),
            ("Permissions",   {"fields": ("is_active", "is_staff", "is_superuser", "role", "groups", "user_permissions")}),
            ("Dates",         {"fields": ("last_login", "date_joined")}),
        )




    #list_display = ("name", "email", "role", "created_at")
    #search_fields = ("name", "email")
    #list_filter   = ("role",)