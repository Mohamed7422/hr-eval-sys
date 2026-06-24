from django.core.management.base import BaseCommand
from evaluation_app.models import Department, SubDepartment, Section, SubSection, EmployeePlacement

def recompute(model, field_name):
    for obj in model.objects.all():
        count = EmployeePlacement.objects.filter(**{field_name: obj}).count()
        obj.employee_count = count
        obj.save(update_fields=["employee_count"])

class Command(BaseCommand):
    help = "Recompute employee_count for all hierarchy units."

    def handle(self, *args, **options):
        recompute(Department, "department")
        recompute(SubDepartment, "sub_department")
        recompute(Section, "section")
        recompute(SubSection, "sub_section")
        self.stdout.write(self.style.SUCCESS("Recomputed all counts."))