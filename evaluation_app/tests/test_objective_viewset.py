import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from evaluation_app.models import Objective, Evaluation, EvalStatus, EvalType, ManagerialLevel


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_evaluation(db, create_employee):
    def _create_evaluation(**kw):
        emp = kw.pop("employee", None) or create_employee()
        defaults = dict(
            employee=emp,
            period="2024-Q4",
            type=EvalType.ANNUAL,
            status=EvalStatus.DRAFT,
            obj_weight_pct=60,
            comp_weight_pct=40,
        )
        defaults.update(kw)
        return Evaluation.objects.create(**defaults)
    return _create_evaluation


@pytest.mark.django_db
class TestObjectiveViewSetPermissionsAndCRUD:
    def test_admin_can_list_all_objectives(self, api_client, create_evaluation, create_user):
        # create two objectives under different employees
        admin = create_user(role="ADMIN")
        ev1 = create_evaluation()
        ev2 = create_evaluation()
        Objective.objects.create(evaluation=ev1, title="O1", description="", weight=50)
        Objective.objects.create(evaluation=ev2, title="O2", description="", weight=50)

        api_client.force_authenticate(user=admin)
        url = reverse("objectives-list")
        res = api_client.get(url)
        assert res.status_code == 200
        # admin should see both
        assert len(res.data) >= 2

    def test_emp_sees_only_own_objectives(self, api_client, create_evaluation, create_user):
        emp_user = create_user(role="EMP")
        other_user = create_user(role="EMP")
        # attach employee profile via fixture helper create_evaluation -> create_employee
        ev_own = create_evaluation(employee=emp_user.employee_profile)
        ev_other = create_evaluation(employee=other_user.employee_profile)
        o1 = Objective.objects.create(evaluation=ev_own, title="Self O1", description="", weight=50)
        Objective.objects.create(evaluation=ev_other, title="Other O1", description="", weight=50)

        api_client.force_authenticate(user=emp_user)
        url = reverse("objectives-list")
        res = api_client.get(url)
        assert res.status_code == 200
        # ensure only own
        ids = [row["id"] for row in res.data]
        assert o1.id in ids
        # should not include other's objective
        assert all(obj.evaluation.employee == emp_user.employee_profile for obj in Objective.objects.filter(id__in=ids))

    def test_emp_cannot_create_for_other_or_non_self_eval(self, api_client, create_evaluation, create_user):
        emp_user = create_user(role="EMP")
        other_user = create_user(role="EMP")
        # self-eval allowed only when evaluation belongs to the same employee and status SELF_EVAL
        self_eval = create_evaluation(employee=emp_user.employee_profile, status=EvalStatus.SELF_EVAL)
        other_eval = create_evaluation(employee=other_user.employee_profile, status=EvalStatus.SELF_EVAL)
        not_self_status = create_evaluation(employee=emp_user.employee_profile, status=EvalStatus.DRAFT)

        api_client.force_authenticate(user=emp_user)
        url = reverse("objectives-list")

        # allowed: self user + SELF_EVAL
        ok_payload = {"evaluation": self_eval.id, "title": "My obj", "description": "", "weight": 50}
        ok_res = api_client.post(url, ok_payload, format="json")
        assert ok_res.status_code == 201

        # forbidden: different employee even if SELF_EVAL
        bad_payload = {"evaluation": other_eval.id, "title": "Nope", "description": "", "weight": 50}
        bad_res = api_client.post(url, bad_payload, format="json")
        assert bad_res.status_code in (403, 401)

        # forbidden: same employee but status not SELF_EVAL
        bad_payload2 = {"evaluation": not_self_status.id, "title": "Nope2", "description": "", "weight": 50}
        bad_res2 = api_client.post(url, bad_payload2, format="json")
        assert bad_res2.status_code in (403, 401)

    def test_update_refreshes_weight_and_returns_serialized(self, api_client, create_evaluation, create_user):
        admin = create_user(role="ADMIN")
        ev = create_evaluation(status=EvalStatus.DRAFT)
        obj = Objective.objects.create(evaluation=ev, title="Edit me", description="", weight=10)

        api_client.force_authenticate(user=admin)
        url = reverse("objectives-detail", args=[obj.id])
        res = api_client.patch(url, {"title": "Edited", "weight": 20}, format="json")
        assert res.status_code == 200
        assert res.data["title"] == "Edited"
        # weight field exists in serializer; ensure it returns updated value
        obj.refresh_from_db()
        assert res.data["weight"] == obj.weight

    def test_destroy_returns_custom_message(self, api_client, create_evaluation, create_user):
        admin = create_user(role="ADMIN")
        ev = create_evaluation(status=EvalStatus.DRAFT)
        obj = Objective.objects.create(evaluation=ev, title="Del", description="", weight=10)

        api_client.force_authenticate(user=admin)
        url = reverse("objectives-detail", args=[obj.id])
        res = api_client.delete(url)
        # custom Response with message and 204
        assert res.status_code == 204
        assert Objective.objects.filter(id=obj.id).count() == 0
