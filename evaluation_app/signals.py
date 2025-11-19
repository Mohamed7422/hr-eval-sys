from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from evaluation_app.models import (
    Employee, EmployeePlacement, Department, SubDepartment, Section, SubSection, Objective, Competency
)
from evaluation_app.services.objective_math import recalculate_objective_weights
from evaluation_app.services.competency_math import recalculate_competency_weights
from evaluation_app.services.evaluation_math import calculate_evaluation_score
import json


# ----helpers----
def _bump(model,pk,delta):
    if pk:
        model.objects.filter(pk=pk).update(employee_count=F("employee_count")+delta)

def _target_tuple(obj):
    return (obj.department_id, obj.sub_department_id, obj.section_id, obj.sub_section_id)

# ----placement counters----
@receiver(pre_save, sender=EmployeePlacement)
def _stash_old_targets(sender, instance, **kwargs):

    if instance.pk and not instance._state.adding:
        try:
            old = EmployeePlacement.objects.get(pk=instance.pk)
            instance._old_targets = _target_tuple(old)
        except EmployeePlacement.DoesNotExist:
            instance._old_targets = (None, None, None, None)
    else:
        instance._old_targets = (None, None, None, None) 

@receiver(post_save, sender=EmployeePlacement)
def _update_counts_on_save(sender, instance, created, **kwargs):
    old_dept, old_subdept, old_sect, old_subsect = getattr(instance, '_old_targets', (None, None, None, None))
    new_dept, new_subdept, new_sect, new_subsect = _target_tuple(instance)
    if not created:
       if old_dept and old_dept != new_dept:     _bump(Department,     old_dept,    -1)
       if old_subdept and old_subdept != new_subdept: _bump(SubDepartment,  old_subdept,  -1)
       if old_sect and old_sect != new_sect:       _bump(Section,        old_sect,     -1)
       if old_subsect and old_subsect != new_subsect: _bump(SubSection,  old_subsect,  -1) 

    #increment the new ones
    if new_dept:        _bump(Department,     new_dept,    +1)
    if new_subdept:     _bump(SubDepartment,  new_subdept, +1)
    if new_sect:       _bump(Section,        new_sect,    +1)
    if new_subsect:    _bump(SubSection,     new_subsect, +1)

@receiver(post_delete, sender=EmployeePlacement)
def _update_counts_on_delete(sender, instance, **kwargs):
    _bump(Department,     instance.department_id,    -1)
    _bump(SubDepartment,  instance.sub_department_id, -1)
    _bump(Section,        instance.section_id,       -1)
    _bump(SubSection,     instance.sub_section_id,   -1)

# ---------------- warnings_count sync ------------------
@receiver(pre_save, sender=Employee)
def _sync_warnings_count(sender, instance, **kwargs):
    
     w = instance.warning
     if isinstance(w, str):
         try:
             w = json.loads(w)
         except ValueError:
             w = []
     if not isinstance(w, (list, tuple)):
         w = [] if w is None else [w]
     instance.warning_count = len(w)       



#-------------------------------------------
# Resplit weights whenever objectives changed (create, update, delete)

@receiver(post_save,sender=Objective)
def _objective_saved(sender, instance:Objective, created,update_fields=None ,**kwargs):
    if update_fields:
        uf = set(update_fields)
        if uf.issubset({"weight","updated_at"}):
            return
    recalculate_objective_weights(instance.evaluation)


@receiver(post_delete,sender=Objective)
def _objective_deleted(sender, instance:Objective, **kwargs):
    recalculate_objective_weights(instance.evaluation)


#-------------------------------------------
# Resplit weights whenever competencies changed (create, update, delete)
@receiver(post_save, sender=Competency)
def _competency_saved(sender, instance: Competency, **kwargs):
    recalculate_competency_weights(instance.evaluation)

@receiver(post_delete, sender=Competency)
def _competency_deleted(sender, instance: Competency, **kwargs):
    recalculate_competency_weights(instance.evaluation)


#-------------------------------------------
@receiver([post_save, post_delete], sender=Objective)
def _objective_changed(sender, instance, **kwargs):
    calculate_evaluation_score(instance.evaluation, persist=True)

@receiver([post_save, post_delete], sender=Competency)
def _competency_changed(sender, instance, **kwargs):
    calculate_evaluation_score(instance.evaluation, persist=True)
#-------------------------------------------


@receiver(post_save, sender=EmployeePlacement)
def update_employee_placement_cache(sender, instance, created, **kwargs):
    """Sync Employee cache when placement changes"""
    employee = instance.employee
    
    # Build path
    path_parts = []
    if instance.department:
        path_parts.append(instance.department.name)
    if instance.sub_department:
        path_parts.append(instance.sub_department.name)
    if instance.section:
        path_parts.append(instance.section.name)
    if instance.sub_section:
        path_parts.append(instance.sub_section.name)
    
    # Get manager from deepest level
    manager = None
    if instance.sub_section and instance.sub_section.manager:
        manager = instance.sub_section.manager
    elif instance.section and instance.section.manager:
        manager = instance.section.manager
    elif instance.sub_department and instance.sub_department.manager:
        manager = instance.sub_department.manager
    elif instance.department and instance.department.manager:
        manager = instance.department.manager
    
    # Update cache
    employee.latest_placement_id = instance.placement_id
    employee.dept_path = " › ".join(path_parts)
    employee.direct_manager_name = manager.name if manager else ""
    employee.direct_manager_id = manager.user_id if manager else None
    employee.save(update_fields=[
        'latest_placement_id', 'dept_path', 
        'direct_manager_name', 'direct_manager_id'
    ])