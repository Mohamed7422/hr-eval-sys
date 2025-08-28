from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from evaluation_app.models import (
    Employee, EmployeePlacement, Department, SubDepartment, Section, SubSection
)
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