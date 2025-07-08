# evaluation_app/management/commands/seed_hr.py
from uuid import uuid4
from django.core.management.base import BaseCommand
from django.utils import timezone
from evaluation_app import models as m


class Command(BaseCommand):
    help = "Seed database with dummy HR-Evaluation data."

    def handle(self, *args, **options):
        now = timezone.now()

        # helper
        def mk_user(name, email, role, title):
            return m.User.objects.get_or_create(
                email=email,
                defaults=dict(
                    user_id=uuid4(),
                    name=name,
                    role=role,
                    title=title,
                    created_at=now,
                ),
            )[0]

        # 1) users
        admin_u = mk_user("Alice Admin", "admin@acme.com", m.Role.ADMIN, "Head of IT")
        hod_u   = mk_user("Bob HOD",     "bob@acme.com",   m.Role.HOD,   "Sales Director")
        lm_u    = mk_user("Carol LM",    "carol@acme.com", m.Role.LM,    "Sales Manager")
        emp_u   = mk_user("Dave Emp",    "dave@acme.com",  m.Role.EMP,   "Sales Rep")

        # 2) company
        acme, _ = m.Company.objects.get_or_create(
            name="ACME Corp",
            defaults=dict(
                company_id=uuid4(),
                address="123 Industrial Ave",
                industry="Manufacturing",
                size=m.CompanySize.MEDIUM,
                created_at=now,
            ),
        )

        # 3) departments (manager NOT NULL)
        sales, _ = m.Department.objects.get_or_create(
            name="Sales",
            company=acme,
            defaults=dict(
                department_id=uuid4(),
                employee_count=0,
                manager=hod_u,
                created_at=now,
            ),
        )

        rnd, _ = m.Department.objects.get_or_create(
            name="R&D",
            company=acme,
            defaults=dict(
                department_id=uuid4(),
                employee_count=0,
                manager=admin_u,
                created_at=now,
            ),
        )

        # 4) employees
        def mk_emp(user, lvl):
            return m.Employee.objects.get_or_create(
                user=user,
                defaults=dict(
                    employee_id=uuid4(),
                    managerial_level=lvl,
                    status=m.EmpStatus.ACTIVE,
                    join_date=timezone.datetime(2023, 1, 15).date(),
                    company=acme,
                ),
            )[0]

        hod_emp   = mk_emp(hod_u,  m.ManagerialLevel.MIDDLE)
        lm_emp    = mk_emp(lm_u,   m.ManagerialLevel.SUPERVISORY)
        sales_emp = mk_emp(emp_u,  m.ManagerialLevel.IC)

        m.EmployeeDepartment.objects.get_or_create(employee=hod_emp,   department=sales)
        m.EmployeeDepartment.objects.get_or_create(employee=lm_emp,    department=sales)
        m.EmployeeDepartment.objects.get_or_create(employee=sales_emp, department=sales)

        # 5) weights config (once)
        for lvl, core, lead, func in [
            (m.ManagerialLevel.IC,          40,  0, 60),
            (m.ManagerialLevel.SUPERVISORY, 30, 30, 40),
            (m.ManagerialLevel.MIDDLE,      30, 40, 30),
        ]:
            m.WeightsConfiguration.objects.get_or_create(
                level_name=lvl,
                defaults=dict(
                    core_weight=core,
                    leadership_weight=lead,
                    functional_weight=func,
                    competency_weight=40,
                    objective_weight=60,
                ),
            )

        # 6) evaluation + details
        eval_q1, _ = m.Evaluation.objects.get_or_create(
            employee=sales_emp,
            period="2025-Q1",
            defaults=dict(
                evaluation_id=uuid4(),
                type=m.EvalType.QUARTERLY,
                status=m.EvalStatus.DRAFT,
                reviewer=lm_u,
                created_at=now,
            ),
        )

        obj1, _ = m.Objective.objects.get_or_create(
            evaluation=eval_q1,
            title="Increase Monthly Sales by 10%",
            defaults=dict(
                objective_id=uuid4(),
                weight=30,
                status=m.ObjectiveState.IN_PROGRESS,
                created_at=now,
            ),
        )

        comp1, _ = m.Competency.objects.get_or_create(
            evaluation=eval_q1,
            name="Product Knowledge",
            defaults=dict(
                competence_id=uuid4(),
                category=m.CompetencyCategory.CORE,
                required_level=8,
                actual_level=6,
                weight=20,
                created_at=now,
            ),
        )

        m.EmployeeObjective.objects.get_or_create(
            employee=sales_emp, objective=obj1, evaluation=eval_q1
        )
        m.EmployeeCompetency.objects.get_or_create(
            employee=sales_emp, competency=comp1, evaluation=eval_q1
        )

        self.stdout.write(self.style.SUCCESS("✅  Dummy data inserted."))
