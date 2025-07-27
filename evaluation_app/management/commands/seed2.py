# evaluation_app/management/commands/seed2.py

from uuid import uuid4
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from evaluation_app import models as ev

class Command(BaseCommand):
    help = """
    Seed #2 ― one company, one department,
    one Line-Manager user (+profile) and
    one Employee user (+profile).
    """

    def handle(self, *args, **options):
        User = get_user_model()
        now  = timezone.now()

        # ─── 1) COMPANY ───────────────────────────────────
        novo = ev.Company.objects.create(
            company_id = uuid4(),
            name       = "NovoTech Ltd.",
            address    = "99 Innovation Way",
            industry   = "Software",
            size       = ev.CompanySize.SMALL,
            created_at = now,
        )

        #Line Manager User
        lm_user = User.objects.create_user(
            username = "lm2",
            email    = "lm2@novotech.com",
            password = "Lm2Pass!",
            role     = "LM",
            name     = "Lara Manager",
        )

        # ─── 2) DEPARTMENT ─────────────────────────────────
        dev_dept = ev.Department.objects.create(
            department_id  = uuid4(),
            name           = "Development",
            employee_count = 0,
            manager        = lm_user,
            company        = novo,
            created_at     = now,
        )

        # ─── 3) USERS ─────────────────────────────────────
       
        emp_user = User.objects.create_user(
            username = "emp2",
            email    = "emp2@novotech.com",
            password = "Emp2Pass!",
            role     = "EMP",
            name     = "Ethan Dev",
        )

        # ─── 4) EMPLOYEE PROFILES ──────────────────────────
        lm_emp = ev.Employee.objects.create(
            employee_id      = uuid4(),
            managerial_level = ev.ManagerialLevel.SUPERVISORY,
            status           = ev.EmpStatus.ACTIVE,
            join_date        = now.date(),
            user             = lm_user,
            company          = novo,
        )
        emp_emp = ev.Employee.objects.create(
            employee_id      = uuid4(),
            managerial_level = ev.ManagerialLevel.IC,
            status           = ev.EmpStatus.ACTIVE,
            join_date        = now.date(),
            user             = emp_user,
            company          = novo,
        )

        # ─── 5) LINK EMPLOYEES → DEPARTMENT ──────────────
        ev.EmployeeDepartment.objects.bulk_create([
            ev.EmployeeDepartment(employee=lm_emp,  department=dev_dept),
            ev.EmployeeDepartment(employee=emp_emp, department=dev_dept),
        ])
        dev_dept.manager         = lm_user
        dev_dept.employee_count  = 2
        dev_dept.save(update_fields=["manager", "employee_count"])

        # report success
        self.stdout.write(self.style.SUCCESS(
            f"✅ Seed-2 loaded: company={novo.name}, "
            f"dept={dev_dept.name}, LM={lm_user.username}, Emp={emp_user.username}"
        ))
