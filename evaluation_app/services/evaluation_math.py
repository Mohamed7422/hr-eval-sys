
from evaluation_app.models import Evaluation, WeightsConfiguration
from evaluation_app.services.objective_math import calculate_objectives_score
from evaluation_app.services.competency_math import calculate_competencies_score
from decimal import Decimal
def calculate_evaluation_score(evaluation: Evaluation, *
                                , cap_at_100: bool = True, persist:bool = False ) -> float:
    
    # Compute the two block scores (0...100)
    objectives_score = Decimal(str (calculate_objectives_score(evaluation, cap_at_100=cap_at_100)))
    competencies_score =Decimal(str (calculate_competencies_score(evaluation, cap_at_100=cap_at_100))) # calculate_competencies_score(evaluation, cap_at_100=cap_at_100)
    
    # Use snapshot weights instead of WeightsConfiguration
    obj_weight = Decimal(str(evaluation.obj_weight_pct or 0))
    comp_weight = Decimal(str(evaluation.comp_weight_pct or 0))

    # Managerial-level block weights (percentages)
    try:
        weights_per_level = WeightsConfiguration.objects.get(level_name = evaluation.employee.managerial_level)
        objectives_weight =  Decimal(str(weights_per_level.objective_weight or 0)) 
        competencies_weight =  Decimal(str(weights_per_level.competency_weight or 0)) 
    except WeightsConfiguration.DoesNotExist:
        return 0.0

    # Normalize if they don't sum to 100
    total_weight = obj_weight + comp_weight
    if total_weight > 0 and total_weight != Decimal("100"):
        factor = Decimal("100") / total_weight # 100 / (objective_weight + competency_weight) 
        obj_weight *= factor 
        comp_weight *= factor 

    # Compute the evaluation score 
    evlauation_score = ((obj_weight * objectives_score) + (comp_weight * competencies_score)) / Decimal("100")    
    evlauation_score = evlauation_score.quantize(Decimal("0.01"))


    if persist: 
       Evaluation.objects.filter(pk=evaluation.pk).update(score=evlauation_score)
       evaluation.score = evlauation_score
      
    return float(evlauation_score)





