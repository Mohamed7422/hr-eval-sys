from django.db import migrations, models

def populate_employee_placement_cache(apps, schema_editor):
    """Populate cached fields from existing EmployeePlacement records"""
    Employee = apps.get_model('evaluation_app', 'Employee')
    EmployeePlacement = apps.get_model('evaluation_app', 'EmployeePlacement')
    
    for employee in Employee.objects.all():
        # Get latest placement for this employee
        placement = (EmployeePlacement.objects
                     .filter(employee=employee)
                     .select_related(
                         'department',
                         'sub_department',
                         'section',
                         'sub_section',
                         'sub_section__manager',
                         'section__manager',
                         'sub_department__manager',
                         'department__manager'
                     )
                     .order_by('-assigned_at')
                     .first())
        
        if placement:
            # Build org path
            path_parts = []
            if placement.department:
                path_parts.append(placement.department.name)
            if placement.sub_department:
                path_parts.append(placement.sub_department.name)
            if placement.section:
                path_parts.append(placement.section.name)
            if placement.sub_section:
                path_parts.append(placement.sub_section.name)
            
            # Get manager from deepest level
            manager = None
            if placement.sub_section and placement.sub_section.manager:
                manager = placement.sub_section.manager
            elif placement.section and placement.section.manager:
                manager = placement.section.manager
            elif placement.sub_department and placement.sub_department.manager:
                manager = placement.sub_department.manager
            elif placement.department and placement.department.manager:
                manager = placement.department.manager
            
            # Update cache fields
            employee.latest_placement_id = placement.placement_id
            employee.dept_path = " › ".join(path_parts)
            employee.direct_manager_name = manager.name if manager else ""
            employee.direct_manager_id = manager.user_id if manager else None
            employee.save(update_fields=[
                'latest_placement_id', 'dept_path',
                'direct_manager_name', 'direct_manager_id'
            ])

class Migration(migrations.Migration):

    dependencies = [
        ('evaluation_app', '0015_backfill_weight_snapshots'),   
    ]

    operations = [
        # Add the new cached fields
        migrations.AddField(
            model_name='employee',
            name='latest_placement_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='dept_path',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='employee',
            name='direct_manager_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='employee',
            name='direct_manager_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        # Populate the cached data
        migrations.RunPython(populate_employee_placement_cache),
    ]