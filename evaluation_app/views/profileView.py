# profiles/views.py
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from evaluation_app.models import EmployeePlacement, EmpStatus
from evaluation_app.serializers.profile_serializer import MyProfileSerializer

User = get_user_model()

class MyProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = MyProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        latest_placements = (
            EmployeePlacement.objects.select_related(
                "company",
                "department","department__manager",
                "sub_department","sub_department__manager","sub_department__department",
                "section","section__manager","section__sub_department__department",
                "sub_section","sub_section__manager","sub_section__section__sub_department__department",
            ).order_by("-assigned_at")
        )

        return (User.objects
            .filter(pk=self.request.user.pk)
            .select_related("employee_profile__company")
            .prefetch_related(
                Prefetch(
                    "employee_profile__employee_placements",
                    queryset=latest_placements,
                    to_attr="placements_cache"
                )
            )
        )

    def get_object(self):
       return self.get_queryset().get()

    def perform_destroy(self, instance):
        # soft-deactivate user + inactivate employment if any
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        emp = getattr(instance, "employee_profile", None)
        if emp:
            emp.status = EmpStatus.INACTIVE
            emp.save(update_fields=["status"])
