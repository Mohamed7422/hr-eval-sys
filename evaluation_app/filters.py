import django_filters as filters
from evaluation_app.models import Objective, Competency
class ObjectiveFilter(filters.FilterSet):
    # expose nice query params…
    evaluation_id = filters.UUIDFilter(field_name="evaluation__evaluation_id", lookup_expr="exact")
    employee_id   = filters.UUIDFilter(field_name="evaluation__employee__employee_id", lookup_expr="exact")
    status        = filters.CharFilter(field_name="status", lookup_expr="exact")  # use keys e.g. IN_PROGRESS

    class Meta:
        model = Objective
        fields = ["evaluation_id", "employee_id", "status"]

class CompetencyFilter(filters.FilterSet):
    # expose nice query params…
    evaluation_id = filters.UUIDFilter(field_name="evaluation__evaluation_id", lookup_expr="exact")
    employee_id   = filters.UUIDFilter(field_name="evaluation__employee__employee_id", lookup_expr="exact")
    category       = filters.CharFilter(field_name="category", lookup_expr="exact")  # use keys e.g. COMMUNICATION

    class Meta:
        model = Competency
        fields = ["evaluation_id", "employee_id", "category"]
