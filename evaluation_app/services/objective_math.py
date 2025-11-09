
from evaluation_app.models import Evaluation, Objective, WeightsConfiguration
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
import logging 

def _d(x) -> Decimal:
    return Decimal(str(x))

def _round2(x: float | Decimal) -> float:
    return float(Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

TOTAL_WEIGHT = Decimal('100.00')
CENT = Decimal('0.01')
 
def recalculate_objective_weights(evaluation:Evaluation) -> None:
    """
    Distribute weights equally among all objectives of the evaluation,
    using a fixed total of 100.00%. Sum is guaranteed to be exactly 100.00.
    (We round down to 2dp and give leftover cents to the first few items.)
    """
  
    #Get Objectives count.
    qs = (evaluation.objective_set
          .order_by('created_at',"objective_id")
          .only("pk","weight"))
    
    objectives_count =qs.count()
    if objectives_count == 0:
            return
    
    # Even share in percent
    even = _d(100) / _d(objectives_count)

    # First n-1 objectives get rounded even; last gets the remainder so sum = 100.00
    weights = []
    for _ in range(max(0, objectives_count - 1)):
        weights.append(_d(even).quantize(CENT, rounding=ROUND_HALF_UP)) 
    used = sum(weights, _d(0))
    weights.append((_d(100) - used).quantize(CENT, rounding=ROUND_HALF_UP))

    objs = list(qs)
    changed = []
    for obj, w in zip(objs, weights):
        if _d(obj.weight or 0) != w:
            obj.weight = float(w)
            changed.append(obj)

    if not changed:
        return

    # Do it atomically and without firing post_save
    with transaction.atomic():
        Objective.objects.bulk_update(changed, ["weight"])
        # If you want updated_at to move (bulk_update skips auto_now):
        if hasattr(Objective, "updated_at"):
            Objective.objects.filter(pk__in=[o.pk for o in changed]).update(updated_at=timezone.now())
            
     # ---------------------------------------------------------------#

def calculate_objectives_score(
    evaluation: Evaluation,
    *,
    cap_at_100: bool = True,
    return_breakdown: bool = False,
) -> float | tuple[float, float, float]:
    """
    1) Subtotal (percentage points 0..100): sum((achieved/target) * weight%)
       - weights are assumed to already sum to 100 (I have it done on recalculate_objective_weights())
       - if cap_at_100=True, each ratio is clamped to [0, 1]
    2) Weighted objectives score = (subtotal / 100) * objective_weight_from_ManagerialLevel

    Returns:
        - default: weighted objectives score (float, 2dp)
        - if return_breakdown=True: (subtotal_pct, objective_weight_pct, weighted_score)
    """
    subtotal = Decimal("0")

    for obj in evaluation.objective_set.all():
        
        try:
          logging.info(f"Calculating score for objective {obj.objective_id}")
        
          target = _d(float(obj.target)) if obj.target else Decimal("0")
          if target <= 0:
              continue
          achieved = _d(float(obj.achieved)) if obj.achieved else Decimal("0")
          ratio = achieved / target
          if cap_at_100:# clamp to [0, 1]
              if ratio < 0:
                  ratio = Decimal("0")
              if ratio > 1:
                  ratio = Decimal("1")
          weight_percent = _d(obj.weight) if obj.weight is not None else Decimal("0")  # each objective’s % share (sums to 100)
          subtotal += ratio * weight_percent
        except Exception as e:  
          logging.error(f"Error calculating score for objective {obj.objective_id}: {e}")
          continue  

    subtotal = subtotal.quantize(CENT)  # e.g., 72.50 (% points)

    # Pull the managerial-level objective weight (e.g., IC might have 60%)
    obj_weight_percent = Decimal("0")
    try:
       # ml_weights = WeightsConfiguration.objects.get(level_name=evaluation.employee.managerial_level)
        obj_weight_percent = _d(evaluation.obj_weight_pct or 0)
    except WeightsConfiguration.DoesNotExist:
        obj_weight_percent = Decimal("0")

    weighted = ((subtotal / Decimal("100")) * obj_weight_percent).quantize(CENT)
   
    if return_breakdown:
        return _round2(subtotal), _round2(obj_weight_percent), _round2(weighted)
    return _round2(weighted)

def compute_objective_score(obj: Objective, *, cap_at_100: bool = True) -> float:
    """
    Score for a single objective = (achieved / target) * weight.
    - Skips if target is missing or <= 0, or achieved is None (returns 0).
    - If cap_at_100, clamp ratio to [0, 1].
    Returns 2-decimal float.
    """
    if obj is None or obj.target is None or float(obj.target) <= 0 or obj.achieved is None:
        return 0.0
    ratio = float(obj.achieved) / float(obj.target)
    if cap_at_100:
        ratio = max(0.0, min(1.0, ratio))
    return _round2(ratio * float(obj.weight or 0.0))