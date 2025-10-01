# evaluation_app/eval_filters/employee_filters.py
import django_filters
from evaluation_app.models import Employee

from accounts.models import Role

class RoleInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    """Accepts CSV (?role=LM,HOD)"""
    pass

class EmployeeFilter(django_filters.FilterSet):
    # Single or multi: ?role=LM  OR  ?role=LM,HOD  OR  ?role=Head-of-Dept,Line%20Manager
    role = RoleInFilter(method="filter_roles")

    company_id   = django_filters.UUIDFilter(field_name="company__company_id")
    company_name = django_filters.CharFilter(field_name="company__name", lookup_expr="iexact")
    
    department_id = django_filters.UUIDFilter(method="filter_department_id")
    class Meta:
        model  = Employee
        fields = ["role", "company_id", "company_name", "department_id"]

    @staticmethod
    def _role_code(raw: str) -> str | None:
        if not raw:
            return None
        s = str(raw).strip()
        # direct code
        codes = {v for v, _ in Role.choices}
        if s in codes:
            return s
        # label (case-insensitive)
        lower = s.lower()
        for code, label in Role.choices:
            if label.lower() == lower:
                return code
        return None

    def filter_roles(self, qs, name, value):
        # `value` is a list from BaseInFilter (handles CSV and repeated params)
        values = value or []
        codes = []
        for v in values:
            code = self._role_code(v)
            if code:
                codes.append(code)
        if not codes:
            return qs.none()
        return qs.filter(user__role__in=codes)

    def filter_department_id(self, qs, name, value): 

     return qs.filter(
        employee_placements__department_id=value
    ).distinct()
 
      