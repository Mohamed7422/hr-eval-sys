from django.db import migrations
from django.utils import timezone

SENTINEL_COMMENT = "[BACKFILL] initial activity log"

def forwards(apps, schema_editor):
    Evaluation  = apps.get_model("evaluation_app", "Evaluation")
    ActivityLog = apps.get_model("evaluation_app", "ActivityLog")

    # Iterate with select_related to avoid N+1 on reviewer/employee.user
    qs = (Evaluation.objects
          .select_related("reviewer", "employee__user"))

    batch = []
    now = timezone.now()
    for ev in qs.iterator():
        # actor preference: reviewer if set, else the employee themself
        actor = ev.reviewer or (ev.employee.user if hasattr(ev, "employee") and ev.employee else None)
        actor_name = getattr(actor, "name", "") if actor else ""
        actor_role = getattr(actor, "role", "") if actor else ""

        # Choose an initial action. Keep it simple/neutral.
        action = "CREATED"
        # If you have a dedicated self-eval status, you may choose this:
        if str(ev.status) == "SELF_EVAL":
            action = "SELF_EVAL_CREATE"

        # Timestamp: use evaluation.created_at if available, else now
        ts = getattr(ev, "created_at", None) or now

        item = ActivityLog(
            evaluation_id=ev.pk,
            activitystatus=ev.status,
            action=action,
            actor_id=getattr(actor, "pk", None),
            actor_name=actor_name,
            actor_role=actor_role,
            comment=SENTINEL_COMMENT,
            is_rejection=False,
            created_at=ts,
            updated_at=ts,
        )
        batch.append(item)

        # Bulk in chunks for large datasets
        if len(batch) >= 2000:
            ActivityLog.objects.bulk_create(batch, ignore_conflicts=True)
            batch.clear()

    if batch:
        ActivityLog.objects.bulk_create(batch, ignore_conflicts=True)


def backwards(apps, schema_editor):
    ActivityLog = apps.get_model("evaluation_app", "ActivityLog")
    ActivityLog.objects.filter(comment=SENTINEL_COMMENT).delete()


class Migration(migrations.Migration):

    dependencies = [
        # IMPORTANT: update this to the actual filename of your ActivityLog migration
        ("evaluation_app", "0018_activitylog"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
