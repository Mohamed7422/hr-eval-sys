import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


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
    employee_count = models.PositiveIntegerField()
    manager       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_departments")
    company       = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments")
    created_at    = models.DateTimeField(default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "name")


class Employee(models.Model):
    employee_id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    managerial_level = models.CharField(max_length=12, choices=ManagerialLevel.choices)
    status           = models.CharField(max_length=16, choices=EmpStatus.choices)
    join_date        = models.DateField()
    created_at       = models.DateTimeField(default=timezone.now)
    updated_at       = models.DateTimeField(auto_now=True)
    user             = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_profile")
    company          = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)

    departments = models.ManyToManyField(Department, through="EmployeeDepartment", related_name="employees")


class EmployeeDepartment(models.Model):
    employee   = models.ForeignKey(Employee, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("employee", "department")


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
    created_at    = models.DateTimeField(default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)

    # convenience M2M via through tables
    objectives   = models.ManyToManyField("Objective", through="EmployeeObjective", related_name="employees")
    competencies = models.ManyToManyField("Competency", through="EmployeeCompetency", related_name="employees")


class Objective(models.Model):
    objective_id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation    = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="objective_set")
    title         = models.CharField(max_length=200)
    description   = models.TextField(blank=True)
    target        = models.TextField(blank=True)
    achieved      = models.TextField(blank=True)
    weight        = models.PositiveSmallIntegerField()
    status        = models.CharField(max_length=15, choices=ObjectiveState.choices)
    created_at    = models.DateTimeField(default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)


class EmployeeObjective(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    employee  = models.ForeignKey(Employee,  on_delete=models.CASCADE)
    objective = models.ForeignKey(Objective, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("evaluation","employee", "objective")


class Competency(models.Model):
    competence_id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation     = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="competency_set")
    name           = models.CharField(max_length=120)
    category       = models.CharField(max_length=12, choices=CompetencyCategory.choices)
    required_level = models.PositiveSmallIntegerField()
    actual_level   = models.PositiveSmallIntegerField()
    weight         = models.PositiveSmallIntegerField()
    description    = models.TextField(blank=True)
    created_at     = models.DateTimeField(default=timezone.now)
    updated_at     = models.DateTimeField(auto_now=True)


class EmployeeCompetency(models.Model):
    evaluation  = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    employee    = models.ForeignKey(Employee,    on_delete=models.CASCADE)
    competency  = models.ForeignKey(Competency,  on_delete=models.CASCADE)

    class Meta:
        unique_together = ("evaluation","employee", "competency")
