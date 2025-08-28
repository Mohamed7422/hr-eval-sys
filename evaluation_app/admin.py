from django.contrib import admin
from .import models as m
 

# ───────────────────────────────
#  Basic inline helpers
# ───────────────────────────────
class EmployeeDepartmentInline(admin.TabularInline):
    model = m.EmployeeDepartment
    extra = 0
    autocomplete_fields = ["department"]


#class EmployeeObjectiveInline(admin.TabularInline):
 #   model = m.EmployeeObjective
 #   extra = 0
 #   autocomplete_fields = ["objective"]


#class EmployeeCompetencyInline(admin.TabularInline):
 #   model = m.EmployeeCompetency
 #  extra = 0
  #  autocomplete_fields = ["competency"]


# ───────────────────────────────
#  Company
# ───────────────────────────────
@admin.register(m.Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "size", "created_at")
    search_fields = ("name", "industry")
    list_filter = ("size",)



def recalc_department_employee_count(modeladmin, request, queryset):
    for d in queryset:
        count = m.EmployeePlacement.objects.filter(department=d).values("employee").distinct().count()
        d.employee_count = count
        d.save(update_fields=["employee_count"])
    modeladmin.message_user(request, f"Recalculated for {queryset.count()} departments.")
recalc_department_employee_count.short_description = "Recalculate employee_count from placements"

# ───────────────────────────────
#  Department
# ───────────────────────────────
@admin.register(m.Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "manager", "employee_count")
    search_fields = ("name", "company__name", "manager__name")
    autocomplete_fields = ["company", "manager"]
    actions = [recalc_department_employee_count]
 


# ───────────────────────────────
#  SubDepartment
# ───────────────────────────────
@admin.register(m.SubDepartment)
class SubDepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "manager", "employee_count", "created_at")
    search_fields = ("name", "department__name", "manager__name")
    autocomplete_fields = ["department", "manager"]
    list_filter = ("department__company",)
    actions = ["recalc_employee_count"]

    @admin.action(description="Recalculate employee_count from placements")
    def recalc_employee_count(self, request, queryset):
        for sd in queryset:
            count = m.EmployeePlacement.objects.filter(sub_department=sd).values("employee").distinct().count()
            sd.employee_count = count
            sd.save(update_fields=["employee_count"])
        self.message_user(request, f"Recalculated for {queryset.count()} sub-departments.")


# ───────────────────────────────
#  Section
# ───────────────────────────────
@admin.register(m.Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "sub_department", "manager", "employee_count", "created_at")
    search_fields = ("name", "sub_department__name", "manager__name")
    autocomplete_fields = ["sub_department", "manager"]
    list_filter = ("sub_department__department__company",)
    actions = ["recalc_employee_count"]

    @admin.action(description="Recalculate employee_count from placements")
    def recalc_employee_count(self, request, queryset):
        for sec in queryset:
            count = m.EmployeePlacement.objects.filter(section=sec).values("employee").distinct().count()
            sec.employee_count = count
            sec.save(update_fields=["employee_count"])
        self.message_user(request, f"Recalculated for {queryset.count()} sections.")


# ───────────────────────────────
#  SubSection
# ─────────────────────────────── 
@admin.register(m.SubSection)
class SubSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "manager", "employee_count", "created_at")
    search_fields = ("name", "section__name", "manager__name")
    autocomplete_fields = ["section", "manager"]
    list_filter = ("section__sub_department__department__company",)
    actions = ["recalc_employee_count"]

    @admin.action(description="Recalculate employee_count from placements")
    def recalc_employee_count(self, request, queryset):
        for ssec in queryset:
            count = m.EmployeePlacement.objects.filter(sub_section=ssec).values("employee").distinct().count()
            ssec.employee_count = count
            ssec.save(update_fields=["employee_count"])
        self.message_user(request, f"Recalculated for {queryset.count()} sub-sections.")



# ───────────────────────────────
#  Employee
# ───────────────────────────────
@admin.register(m.Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "managerial_level", "status", "get_company_name","job_type","branch","employee_code","warning_count", "join_date")
    list_filter  = ("managerial_level", "status", "company", "job_type", "branch")
    search_fields = ("user__name", "user__email","employee_code")
    autocomplete_fields = ["user", "company"]
    inlines = [EmployeeDepartmentInline]

    @admin.display(description="Company")
    def get_company_name(self, obj):
        return obj.company.name if obj.company else "-"


# ───────────────────────────────
#  Employee-Placement
# ───────────────────────────────
@admin.register(m.EmployeePlacement)
class EmployeePlacementAdmin(admin.ModelAdmin):
    list_display = ("employee", "company", "unit", "assigned_at")
    search_fields = (
        "employee__user__name", "employee__user__email",
        "department__name", "sub_department__name",
        "section__name", "sub_section__name"
    )
    autocomplete_fields = ["employee", "company", "department", "sub_department", "section", "sub_section"]
    list_filter = ("company",)

    @admin.display(description="Org Unit")
    def unit(self, obj):
        if obj.department:
            return f"Dept: {obj.department.name}"
        if obj.sub_department:
            return f"SubDept: {obj.sub_department.name}"
        if obj.section:
            return f"Section: {obj.section.name}"
        if obj.sub_section:
            return f"SubSection: {obj.sub_section.name}"
        return "-"
    
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



#-----

