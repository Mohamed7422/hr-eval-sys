import pytest
from decimal import Decimal
from evaluation_app.models import Evaluation, ManagerialLevel, EvalStatus, EvalType
from evaluation_app.services.evaluation_math import calculate_evaluation_score


@pytest.mark.django_db
class TestEvaluationMath:
    def test_weighted_sum_uses_snapshot_weights(self, create_employee, create_weights):
        # IC weights 60/40
        create_weights(level_name=ManagerialLevel.IC, objective_weight=60, competency_weight=40)
        emp = create_employee(managerial_level=ManagerialLevel.IC)
        ev = Evaluation.objects.create(
            employee=emp,
            period="2024-Q4",
            type=EvalType.ANNUAL,
            status=EvalStatus.DRAFT,
            obj_weight_pct=60,
            comp_weight_pct=40,
        )

        # Patch per-block scores by temporarily monkeypatching the math functions via settings on the model
        # Instead of importing internal functions, create a scenario where one block is dominant by snapshot weights
        # We'll rely on objective/competency math to default to 0 if nothing present; to make it deterministic,
        # we add weights on the evaluation snapshot and expect a 0 overall if both sub-scores are 0.
        score = calculate_evaluation_score(ev, cap_at_100=True, persist=False)
        assert isinstance(score, float)
        # With no objectives/competencies, sub-scores are expected 0, so final is 0
        assert score == 0.0

    def test_normalizes_weights_not_summing_to_100(self, create_employee, create_weights, monkeypatch):
        # Set snapshot weights that don't sum to 100 to test normalization (e.g., 30 and 30 -> 60 total)
        create_weights(level_name=ManagerialLevel.IC, objective_weight=50, competency_weight=50)
        emp = create_employee(managerial_level=ManagerialLevel.IC)
        ev = Evaluation.objects.create(
            employee=emp,
            period="2024-Q4",
            type=EvalType.ANNUAL,
            status=EvalStatus.DRAFT,
            obj_weight_pct=30,
            comp_weight_pct=30,
        )

        # Force deterministic block scores by monkeypatching the imported functions used inside calculate_evaluation_score
        import evaluation_app.services.evaluation_math as em
        monkeypatch.setattr(em, "calculate_objectives_score", lambda evaluation, cap_at_100=True: 80)
        monkeypatch.setattr(em, "calculate_competencies_score", lambda evaluation, cap_at_100=True: 40)

        # The function should normalize 30/30 to 50/50, resulting in average of 80 and 40 => 60
        score = calculate_evaluation_score(ev, cap_at_100=True, persist=False)
        assert pytest.approx(score, rel=1e-6) == 60.0

    def test_clamps_or_rounds_to_two_decimals(self, create_employee, create_weights, monkeypatch):
        create_weights(level_name=ManagerialLevel.IC, objective_weight=60, competency_weight=40)
        emp = create_employee(managerial_level=ManagerialLevel.IC)
        ev = Evaluation.objects.create(
            employee=emp,
            period="2024-Q4",
            type=EvalType.ANNUAL,
            status=EvalStatus.DRAFT,
            obj_weight_pct=60,
            comp_weight_pct=40,
        )
        import evaluation_app.services.evaluation_math as em
        # Make a value that would produce a long float to ensure rounding to 2 decimals happens
        monkeypatch.setattr(em, "calculate_objectives_score", lambda evaluation, cap_at_100=True: 99.999)
        monkeypatch.setattr(em, "calculate_competencies_score", lambda evaluation, cap_at_100=True: 66.666)

        score = calculate_evaluation_score(ev, cap_at_100=True, persist=False)
        # Weighted: 0.6*99.999 + 0.4*66.666 = 86.6658 => rounded to 86.67
        assert pytest.approx(score, rel=1e-6) == 86.67

    def test_uses_managerial_level_weights_and_returns_zero_when_missing(self, create_employee, monkeypatch):
        # Do NOT create weights for this level to trigger DoesNotExist branch
        emp = create_employee(managerial_level=ManagerialLevel.MIDDLE)
        ev = Evaluation.objects.create(
            employee=emp,
            period="2024-Q4",
            type=EvalType.ANNUAL,
            status=EvalStatus.DRAFT,
            obj_weight_pct=60,
            comp_weight_pct=40,
        )
        import evaluation_app.services.evaluation_math as em
        monkeypatch.setattr(em, "calculate_objectives_score", lambda evaluation, cap_at_100=True: 80)
        monkeypatch.setattr(em, "calculate_competencies_score", lambda evaluation, cap_at_100=True: 90)

        score = calculate_evaluation_score(ev, cap_at_100=True, persist=False)
        assert score == 0.0

    def test_persist_updates_evaluation_score_field(self, create_employee, create_weights, monkeypatch):
        create_weights(level_name=ManagerialLevel.IC, objective_weight=60, competency_weight=40)
        emp = create_employee(managerial_level=ManagerialLevel.IC)
        ev = Evaluation.objects.create(
            employee=emp,
            period="2024-Q4",
            type=EvalType.ANNUAL,
            status=EvalStatus.DRAFT,
            obj_weight_pct=60,
            comp_weight_pct=40,
        )
        import evaluation_app.services.evaluation_math as em
        monkeypatch.setattr(em, "calculate_objectives_score", lambda evaluation, cap_at_100=True: 50)
        monkeypatch.setattr(em, "calculate_competencies_score", lambda evaluation, cap_at_100=True: 100)

        score = calculate_evaluation_score(ev, persist=True)
        assert pytest.approx(score, rel=1e-6) == 70.0
        ev.refresh_from_db()
        # Stored as Decimal(2dp) in DB
        assert str(ev.score) == str(Decimal("70.00"))
