
from evaluation_app.models import (
    Evaluation, Competency, CompetencyCategory
)
from typing import Dict
from django.db import transaction
from django.utils import timezone

'''_Cat_FIELDS = {
    CompetencyCategory.CORE: "core_weight",
    CompetencyCategory.LEADERSHIP: "leadership_weight",
    CompetencyCategory.FUNCTIONAL: "functional_weight",
}
'''
def _round_to_2dp(value: float) -> float:
    return float(f"{(value or 0):0.2f}")
def category_weights_for_evaluation(evaluation) -> Dict[str, float]:

    """
    Return {category_value: total_weight} for the employee level.
    Missing config/fields -> 0.0
    """



    ''' try:
        weights_per_level = WeightsConfiguration.objects.get(level_name = level)   
    except WeightsConfiguration.DoesNotExist:
        return {cat: 0.0 for cat in _Cat_FIELDS.keys()}

    out = {}
    
    for cat, field in _Cat_FIELDS.items(): 
        out[cat] = getattr(weights_per_level, field, 0.0) or 0.0  
    '''     
    return {
        CompetencyCategory.CORE: float(evaluation.comp_core_pct or 0.0),
        CompetencyCategory.LEADERSHIP: float(evaluation.comp_leadership_pct or 0.0),
        CompetencyCategory.FUNCTIONAL: float(evaluation.comp_functional_pct or 0.0),
    }

def recalculate_competency_weights(evaluation:Evaluation) -> None:
    """
    Split each category's total weight (from WeightsConfiguration for the employee level)
    evenly across competencies "in that category" within this evaluation.

    Uses bulk_update so we don't emit save() signals.
    
    """
    qs = evaluation.competency_set.order_by("created_at", "competence_id")
    comptencies = list(qs)  
    if not comptencies:
        return
    # returned dict : ex: {Core: 30.0, Leadership: 20.0, Functional: 50.0}
    category_weights_totals = category_weights_for_evaluation(evaluation)
    
    # ex: {Core: [comp1, comp2], Leadership: [comp3, comp4], Functional: [comp5, comp6]}
    by_cat: Dict[str, list[Competency]] = {}
    for comp in comptencies:
        by_cat.setdefault(comp.category, []).append(comp)

    now = timezone.now()
    to_update: list[Competency] = []
    with transaction.atomic():
        for cat, items in by_cat.items(): 
            number_of_competencies = len(items)
            # ex: total for Core category is 30.0
            total_weight_for_cat = float(category_weights_totals.get(cat, 0.0))
            
            #1: if number of competencies is 0, continue
            if number_of_competencies == 0:
                continue

            #2: if total weight for category is 0 or less, 
            # zero all competencies in that category and continue
            if total_weight_for_cat <= 0:
             
               for comp in items:
                   
                   if(comp.weight or 0) != 0:
                       comp.weight = 0.0
                       comp.updated_at = now
                       to_update.append(comp)
               continue    
            #3: divide total weight for category by number of competencies for 
            # that category
            even_weight_per_competency  =total_weight_for_cat/number_of_competencies
            running = 0.0 
            for competency in items[:-1]: #-1 means to exclude last competency
                competency_weight_rounded = _round_to_2dp(even_weight_per_competency) 
                running += even_weight_per_competency
                if competency.weight != competency_weight_rounded:
                   competency.weight = competency_weight_rounded
                   competency.updated_at = now
                   to_update.append(competency)

            #4: add the remaining weight to the last competency
            # ex: if number of competencies is 3 and total weight for category is 100.0
            last_competency_weight_rounded = _round_to_2dp(total_weight_for_cat - running)   
            last_competency = items[-1]
            if last_competency.weight != last_competency_weight_rounded:
                last_competency.weight = last_competency_weight_rounded
                last_competency.updated_at = now
                to_update.append(last_competency)

        if to_update: # if to_update is not empty, update comptencies with evenly distributed weights
            Competency.objects.bulk_update(to_update, ["weight", "updated_at"])            


def competency_score(competency: Competency, *, cap_at_100: bool = True) -> float:
    """
    (achieved / target) * weight (optionally clapped to 100%)
    """
    req = float(competency.required_level or 0)
    if req <=0:
        return 0.0
    ratio = float(competency.actual_level or 0) / req
    if cap_at_100:
        ratio = max(0.0, min(1.0, ratio))
    return _round_to_2dp(ratio * float(competency.weight or 0.0))

def calculate_competencies_score(evaluation:Evaluation, *, cap_at_100: bool = True)-> float:
    total = 0.0
    competencies = evaluation.competency_set.only(
        'competence_id', 'required_level', 'actual_level', 'weight'
    ).all()

    for c in competencies:
        total += competency_score(c, cap_at_100=cap_at_100)
    total = _round_to_2dp(total)
    # get the total weight of all competencies in this evaluation based on employee managerial level
    # Get competency weight % from WeightsConfiguration
    
    competency_total_weight = float(evaluation.comp_weight_pct or 0.0)
     
    return _round_to_2dp(total * (competency_total_weight/100))
