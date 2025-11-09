import pytest
from evaluation_app.models import Evaluation, ManagerialLevel, EvalStatus, EvalType
from evaluation_app.services.evaluation_math import calculate_evaluation_score
from evaluation_app.serializers.evaluation_serilizer import EvaluationSerializer


@pytest.mark.django_db
class TestWeightFreezing:
    def test_evaluation_freezes_weights_on_creation(self, create_employee, create_weights):
        weights = create_weights(
            level_name=ManagerialLevel.IC,
            objective_weight=60,
            competency_weight=40,
            core_weight=20,
            leadership_weight=10,
            functional_weight=10,
        )
        employee = create_employee()
        
        serializer = EvaluationSerializer(
            data={
                "employee_id": employee.employee_id,
                "period": "2023-Q4",
                "type": EvalType.ANNUAL,
                "status": EvalStatus.DRAFT
            }
        )
        serializer.is_valid(raise_exception=True)
        eval = serializer.save()
         
        eval.refresh_from_db()

        # these fields must exist on Evaluation and be set on create
        assert eval.obj_weight_pct == weights.objective_weight
        assert eval.comp_weight_pct == weights.competency_weight
        assert eval.comp_core_pct == weights.core_weight
        assert eval.comp_leadership_pct == weights.leadership_weight
        assert eval.comp_functional_pct == weights.functional_weight

    def test_evaluation_score_unchanged_when_weights_updated(self, create_employee, create_weights):
        weights = create_weights(
            level_name=ManagerialLevel.IC,
            objective_weight=60,
            competency_weight=40,
        )
        employee = create_employee(managerial_level=ManagerialLevel.IC)

        eval = Evaluation.objects.create(
            employee=employee,
            period="2023-Q4",
            type=EvalType.ANNUAL,
            status=EvalStatus.DRAFT,
        )

        initial = calculate_evaluation_score(eval, persist=True)

        # change config AFTER evaluation was created
        weights.objective_weight = 70
        weights.competency_weight = 30
        weights.save()

        new = calculate_evaluation_score(eval, persist=True)
        assert initial == new
