import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db.models import Q

# ── Lookup / Enum helpers ────────────────────────────────────────────────

class CompanySize(models.TextChoices):
    SMALL  = "SMALL",  "Small"
    MEDIUM = "MEDIUM", "Medium"
    LARGE  = "LARGE",  "Large"  

class ManagerialLevel(models.TextChoices):
    IC          = "IC",          "Individual Contributor"
    SUPERVISORY = "SUPERVISORY", "Supervisory"
    MIDDLE      = "MIDDLE",      "Middle Management"

class EmpStatus(models.TextChoices):
    ACTIVE   = "ACTIVE",   "Active"
    INACTIVE = "INACTIVE", "Inactive"
    DEFAULT  = "DEFAULT_ACTIVE", "Default Active"

class JobType(models.TextChoices):                
    FULL_TIME         = "FULL_TIME",         "Full-time"
    PART_TIME         = "PART_TIME",         "Part-time"
    FULL_TIME_REMOTE  = "FULL_TIME_REMOTE",  "Full-time Remote"
    PART_TIME_REMOTE  = "PART_TIME_REMOTE",  "Part-time Remote"

class BranchType(models.TextChoices):               
    OFFICE = "OFFICE", "Office"
    STORE  = "STORE",  "Store"


class EvalType(models.TextChoices):
    ANNUAL    = "ANNUAL",    "Annual"
    QUARTERLY = "QUARTERLY", "Quarterly"
    OPTIONAL  = "OPTIONAL",  "Optional"

class EvalStatus(models.TextChoices):
    DRAFT          = "DRAFT",          "Draft"
    PENDING_HOD    = "PENDING_HOD",    "Pending HoD Approval"
    PENDING_HR     = "PENDING_HR",     "Pending HR Approval"
    EMP_REVIEW     = "EMP_REVIEW",     "Employee Review"
    APPROVED       = "APPROVED",       "Approved"
    REJECTED       = "REJECTED",       "Rejected"
    COMPLETED      = "COMPLETED",      "Completed"

class ObjectiveState(models.TextChoices):
    COMPLETED   = "COMPLETED",   "Completed"
    IN_PROGRESS = "IN_PROGRESS", "In-progress"
    NOT_STARTED = "NOT_STARTED", "Not started"

class CompetencyCategory(models.TextChoices):
    CORE        = "CORE",        "Core"
    LEADERSHIP  = "LEADERSHIP",  "Leadership"
    FUNCTIONAL  = "FUNCTIONAL",  "Functional"

# ── Core tables ──────────────────────────────────────────────────────────
class Company(models.Model):
    company_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=180)
    address    = models.TextField()
    industry   = models.CharField(max_length=100)
    size       = models.CharField(max_length=6, choices=CompanySize.choices)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Department(models.Model):
    department_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name          = models.CharField(max_length=120)
    employee_count = models.PositiveIntegerField(default=0)
    manager       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_departments", null=True, blank=True)
    company       = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments")
    created_at    = models.DateTimeField(default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        constraints=[
            models.UniqueConstraint(fields=["company", "name"], name="uniq_dept_per_company")
        ]
        #unique_together = ("company", "name")
 
class SubDepartment(models.Model):
    sub_department_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name              = models.CharField(max_length=120)
    employee_count    = models.PositiveIntegerField(default=0)
    manager           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_sub_departments", null=True, blank=True)
    department        = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="sub_departments")
    created_at        = models.DateTimeField(default=timezone.now)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="uniq_subdept_per_dept")
        ]


class Section(models.Model):
    section_id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name             = models.CharField(max_length=120)
    employee_count   = models.PositiveIntegerField(default=0)
    manager          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_sections", null=True, blank=True)
    sub_department   = models.ForeignKey(SubDepartment, on_delete=models.CASCADE, related_name="sections")
    created_at       = models.DateTimeField(default=timezone.now)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sub_department", "name"], name="uniq_section_per_subdept")
        ]

 
class SubSection(models.Model):
    sub_section_id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name             = models.CharField(max_length=120)
    employee_count   = models.PositiveIntegerField(default=0)
    manager          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_sub_sections", null=True, blank=True)
    section          = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="sub_sections")
    created_at       = models.DateTimeField(default=timezone.now)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["section", "name"], name="uniq_subsection_per_section")
        ]


class Employee(models.Model):
    employee_id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    managerial_level = models.CharField(max_length=12, choices=ManagerialLevel.choices)
    status           = models.CharField(max_length=16, choices=EmpStatus.choices)
    join_date        = models.DateField()
    created_at       = models.DateTimeField(default=timezone.now)
    updated_at       = models.DateTimeField(auto_now=True)
    user             = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_profile")
    company          = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)

    employee_code = models.CharField(max_length=120,blank=True,null=True, default=None)
    warning = models.JSONField(default=list,blank=True) # list of warning strings
    warning_count = models.PositiveSmallIntegerField(default=0)
    job_type = models.CharField(max_length=20, choices=JobType.choices, blank=True, null=True,default=JobType.FULL_TIME)
    location = models.CharField(max_length=180,blank=True) 
    branch = models.CharField(max_length=20, choices=BranchType.choices, blank=True, null=True, default=BranchType.OFFICE)

    # Legacy fields from old system
    #departments = models.ManyToManyField(Department, through="EmployeeDepartment", related_name="employees")

    class Meta:
         
        constraints=[
            models.UniqueConstraint(fields=["company", "employee_code"], 
                                    name="uniq_client_emp_code_per_company",
                                    condition=(Q(employee_code__isnull=False)
                                               & ~Q(employee_code="")) #return list of employees with non-null client_employee_code
                                    )
        ]
        
        
    def save(self, *args, **kwargs):
        # Update warning count before saving
        try:
            self.warning_count = len(self.warning or [])
        except Exception:
            self.warning_count = 0    
        super().save(*args,**kwargs)

class EmployeeDepartment(models.Model):
    #Legacy
    employee   = models.ForeignKey(Employee, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("employee", "department")


class EmployeePlacement(models.Model):
    placement_id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee         = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_placements")
    company          = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="company_placements")
    department       = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="department_placements")
    sub_department   = models.ForeignKey(SubDepartment, on_delete=models.CASCADE, null=True, blank=True, related_name="sub_department_placements")
    section          = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name="section_placements")
    sub_section      = models.ForeignKey(SubSection, on_delete=models.CASCADE, null=True, blank=True, related_name="sub_section_placements")
    assigned_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        # conditional uniqueness per level
        constraints = [
            models.UniqueConstraint(
                fields=["employee"],
                name="uniq_emp_one_placement_per_employee",
            )
        ]

# ── Weight configuration ---------------------------------------------------
class WeightsConfiguration(models.Model):
    level_name        = models.CharField(primary_key=True, max_length=12, choices=ManagerialLevel.choices)
    core_weight       = models.PositiveSmallIntegerField()
    leadership_weight = models.PositiveSmallIntegerField()
    functional_weight = models.PositiveSmallIntegerField()
    competency_weight = models.PositiveSmallIntegerField()
    objective_weight  = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name_plural = "Weights configuration"


# ── Evaluations & related ---------------------------------------------------
class Evaluation(models.Model):
    evaluation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee      = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="evaluations")
    type          = models.CharField(max_length=10, choices=EvalType.choices)
    status        = models.CharField(max_length=20, choices=EvalStatus.choices)
    score         = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    reviewer      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    period        = models.CharField(max_length=20)      # e.g. '2025-Q1'
    created_at    = models.DateTimeField(default=timezone.now) #format "%Y-%m-%d %H:%M:%S"
    updated_at    = models.DateTimeField(auto_now=True) #format "%Y-%m-%d %H:%M:%S"
    
    # Weights percentages
    obj_weight_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    comp_weight_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    comp_core_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    comp_leadership_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    comp_functional_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    # convenience M2M via through tables
    #objectives   = models.ManyToManyField("Objective", through="EmployeeObjective", related_name="employees")
    #competencies = models.ManyToManyField("Competency", through="EmployeeCompetency", related_name="employees")


class Objective(models.Model):
    objective_id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation    = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="objective_set")
    title         = models.CharField(max_length=200)
    description   = models.TextField(blank=True)
    target        = models.TextField(blank=True)
    achieved      = models.TextField(blank=True)
    weight        = models.PositiveSmallIntegerField(null=True, blank=True)
    status        = models.CharField(max_length=15, choices=ObjectiveState.choices)
    created_at    = models.DateTimeField(default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)


#class EmployeeObjective(models.Model):
  #  evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
  #  employee  = models.ForeignKey(Employee,  on_delete=models.CASCADE)
   # objective = models.ForeignKey(Objective, on_delete=models.CASCADE)

  #  class Meta:
    #    unique_together = ("evaluation","employee", "objective")


class Competency(models.Model):
    competence_id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation     = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="competency_set")
    name           = models.CharField(max_length=120)
    category       = models.CharField(max_length=12, choices=CompetencyCategory.choices)
    required_level = models.PositiveSmallIntegerField()
    actual_level   = models.PositiveSmallIntegerField()
    weight         = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    description    = models.TextField(blank=True)
    created_at     = models.DateTimeField(default=timezone.now)
    updated_at     = models.DateTimeField(auto_now=True)


#class EmployeeCompetency(models.Model):
 #   evaluation  = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
  #  employee    = models.ForeignKey(Employee,    on_delete=models.CASCADE)
  #  competency  = models.ForeignKey(Competency,  on_delete=models.CASCADE)

  #  class Meta:
   #     unique_together = ("evaluation","employee", "competency")
