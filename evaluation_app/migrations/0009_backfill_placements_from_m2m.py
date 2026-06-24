from django.db import migrations, transaction

def backfill(apps, schema_editor):
    Employee = apps.get_model("evaluation_app", "Employee")
    Department = apps.get_model("evaluation_app", "Department")
    EmployeePlacement = apps.get_model("evaluation_app", "EmployeePlacement")
    EmployeeDepartment = apps.get_model("evaluation_app", "EmployeeDepartment")

    # For each employee WITHOUT a placement, create one:
    #   • department = first EmployeeDepartment (by pk) if exists, else None
    #   • company = employee.company if set; else department.company if department picked; else skip
    with transaction.atomic():
        qs = (Employee.objects
              .select_related("company")
              .all())

        for emp in qs:
            if EmployeePlacement.objects.filter(employee=emp).exists():
                continue

            rel = (EmployeeDepartment.objects
                   .filter(employee=emp)
                   .select_related("department")
                   .order_by("pk")
                   .first())
            dept = rel.department if rel else None

            company = emp.company or (dept.company if dept else None)
            if company is None:
                # No company and no dept → cannot infer; skip and handle manually later if needed
                continue

            EmployeePlacement.objects.create(
                employee=emp,
                company=company,
                department=dept,  # ok if None
                # sub_department/section/sub_section left NULL; can be patched later
            )

class Migration(migrations.Migration):
    dependencies = [
        ("evaluation_app", "0008_remove_employeeplacement_uniq_emp_dept_and_more"),
    ]
    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]