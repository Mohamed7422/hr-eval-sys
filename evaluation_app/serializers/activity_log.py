from rest_framework import serializers
from django.contrib.auth import get_user_model
from evaluation_app.models import ActivityLog, Evaluation

User = get_user_model()

class ActivityLogSerializer(serializers.ModelSerializer):
    # write
    evaluation_id = serializers.PrimaryKeyRelatedField(
        source="evaluation", queryset=Evaluation.objects.all()
    )
    actor_id = serializers.PrimaryKeyRelatedField(
        source="actor", queryset=User.objects.all(), required=False, allow_null=True
    )

    # read
    actor_name = serializers.CharField(read_only=True)
    actor_role = serializers.CharField(read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            "activitylog_id",
            "evaluation_id",
            "activitystatus",
            "action",
            "actor_id",
            "actor_name",
            "actor_role",
            "comment",
            "is_rejection",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("activitylog_id", "actor_name", "actor_role", "created_at", "updated_at")

    def create(self, validated):
        # default actor = request.user unless explicitly provided and allowed by perms
        req = self.context.get("request")
        if req and not validated.get("actor"):
            u = req.user
            validated["actor"] = u
            validated["actor_name"] = getattr(u, "name", u.get_username())
            validated["actor_role"] = getattr(u, "role", "")
        else:
            # if actor provided, denormalize name/role
            u = validated.get("actor")
            if u:
                validated["actor_name"] = getattr(u, "name", u.get_username())
                validated["actor_role"] = getattr(u, "role", "")
        return super().create(validated)
