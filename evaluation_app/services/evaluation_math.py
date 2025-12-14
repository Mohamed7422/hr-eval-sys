
from evaluation_app.models import Evaluation
from evaluation_app.services.objective_math import calculate_objectives_score
from evaluation_app.services.competency_math import calculate_competencies_score
from decimal import Decimal
def calculate_evaluation_score(
    evaluation: Evaluation,
    *,
    cap_at_100: bool = True,
    persist: bool = False
) -> float:
    """
    Calculate final evaluation score.
    
    Formula:
    Evaluation Score = (Objectives Score × obj_weight_pct / 100) + Competencies Score
    
    Note: Competencies score and objectives score are calculated separately via their own math functions.
    """
     
    objectives_score = calculate_objectives_score(evaluation, cap_at_100=cap_at_100)
    
    competencies_score = calculate_competencies_score(evaluation, cap_at_100=cap_at_100)
     
    evaluation_score = (
        Decimal(str(objectives_score)) + 
        Decimal(str(competencies_score))
    )
    
    evaluation_score = evaluation_score.quantize(Decimal('0.01'))
    
    if persist:
        Evaluation.objects.filter(pk=evaluation.pk).update(
          
            objectives_score=objectives_score,
            competencies_score=competencies_score,
            score=float(evaluation_score)
        )
        evaluation.objectives_score = objectives_score
        evaluation.competencies_score = competencies_score
        evaluation.score = float(evaluation_score)
         
    
    return float(evaluation_score)





 