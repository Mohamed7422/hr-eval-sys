from django.contrib import admin
from .import models as m



# ───────────────────────────────
#  Basic inline helpers
# ───────────────────────────────
class EmployeeDepartmentInline(admin.TabularInline):
    model = m.EmployeeDepartment
    extra = 0
    autocomplete_fields = ["department"]


class EmployeeObjectiveInline(admin.TabularInline):
    model = m.EmployeeObjective
    extra = 0
    autocomplete_fields = ["objective"]


class EmployeeCompetencyInline(admin.TabularInline):
    model = m.EmployeeCompetency
    extra = 0
    autocomplete_fields = ["competency"]


# ───────────────────────────────
#  Company
# ───────────────────────────────
@admin.register(m.Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "size", "created_at")
    search_fields = ("name", "industry")
    list_filter = ("size",)


# ───────────────────────────────
#  Department
# ───────────────────────────────
@admin.register(m.Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "manager", "employee_count")
    search_fields = ("name", "company__name", "manager__name")
    autocomplete_fields = ["company", "manager"]


# ───────────────────────────────
#  User
# ───────────────────────────────
@admin.register(m.User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "created_at")
    search_fields = ("name", "email")
    list_filter = ("role",)


# ───────────────────────────────
#  Employee
# ───────────────────────────────
@admin.register(m.Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "managerial_level", "status", "company", "join_date")
    list_filter  = ("managerial_level", "status", "company")
    search_fields = ("user__name", "user__email")
    autocomplete_fields = ["user", "company"]
    inlines = [EmployeeDepartmentInline, EmployeeObjectiveInline, EmployeeCompetencyInline]


# ───────────────────────────────
#  WeightsConfiguration
# ───────────────────────────────
@admin.register(m.WeightsConfiguration)
class WeightConfigAdmin(admin.ModelAdmin):
    list_display = ("level_name", "core_weight", "leadership_weight",
                    "functional_weight", "competency_weight", "objective_weight")
    list_editable = ("core_weight", "leadership_weight",
                     "functional_weight", "competency_weight", "objective_weight")


# ───────────────────────────────
#  Objective & Competency templates
# ───────────────────────────────
@admin.register(m.Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ("title", "evaluation", "weight", "status")
    autocomplete_fields = ["evaluation"]
    list_filter = ("status",)
    search_fields = ("title", "evaluation__employee__user__name")


@admin.register(m.Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ("name", "evaluation", "category", "weight",
                    "required_level", "actual_level")
    autocomplete_fields = ["evaluation"]
    list_filter = ("category",)
    search_fields = ("name", "evaluation__employee__user__name")


# ───────────────────────────────
#  Evaluation
# ───────────────────────────────
class ObjectiveInline(admin.TabularInline):
    model = m.Objective
    extra = 0
    autocomplete_fields = ["evaluation"]


class CompetencyInline(admin.TabularInline):
    model = m.Competency
    extra = 0
    autocomplete_fields = ["evaluation"]


@admin.register(m.Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "type", "status", "reviewer", "created_at")
    list_filter  = ("type", "status", "period")
    search_fields = ("employee__user__name", "reviewer__name", "period")
    autocomplete_fields = ["employee", "reviewer"]
    inlines = [ObjectiveInline, CompetencyInline]
