
from evaluation_app.models import (
    Evaluation, Competency, CompetencyCategory
)
from typing import Dict
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
def _d(x) -> Decimal:
    """Convert to Decimal safely."""
    return Decimal(str(x))

def _round2(x: float | Decimal) -> float:
    """Round to 2 decimal places."""
    return float(Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

CENT = Decimal('0.01')
 
 
def category_weights_for_evaluation(evaluation) -> Dict[str, float]:

    """
    Return category weights from evaluation snapshot.
    
    Returns:
        Dict mapping category to weight percentage
        Example: {CORE: 15.0, LEADERSHIP: 20.0, FUNCTIONAL: 25.0}
    """   
    return {
        CompetencyCategory.CORE: float(evaluation.comp_core_pct or 0.0),
        CompetencyCategory.LEADERSHIP: float(evaluation.comp_leadership_pct or 0.0),
        CompetencyCategory.FUNCTIONAL: float(evaluation.comp_functional_pct or 0.0),
    }

def validate_competencies_constraints(evaluation: Evaluation) -> None:
    """
    Validate that competencies meet all constraints:
    - Actual level must be 0-4
    - Required level must be 0-4 (typically 4)
    - IF competencies exist, must have competencies for categories with non-zero weights
    
    Note: Competencies are OPTIONAL. If none exist, validation passes.
    Note: Only categories with weight > 0 are required.
          Example: EXECUTIVE level has functional_weight=0, so FUNCTIONAL not required.
    
    Raises:
        ValidationError: If any constraint is violated
    """
    competencies = list(evaluation.competency_set.all())
    
    # If no competencies, that's fine - they're optional
    if len(competencies) == 0:
        return
    
    # Check levels
    for comp in competencies:
        if comp.actual_level < 0 or comp.actual_level > 4:
            raise ValidationError(
                f"Actual level must be between 0 and 4 (Competency: {comp.name})"
            )
        
        if comp.required_level != 4:
            raise ValidationError(
                f"Required level must be 4 (Competency: {comp.name})"
            )
    
    # Get category weights to determine which categories are required
    category_weights = category_weights_for_evaluation(evaluation)
    
    # Only check categories that have non-zero weights
    categories = set(comp.category for comp in competencies)
    
    # Check CORE (if weight > 0)
    if category_weights.get(CompetencyCategory.CORE, 0) > 0:
        if CompetencyCategory.CORE not in categories:
            raise ValidationError(
                "Must have at least one CORE competency (CORE weight is non-zero)"
            )
    
    # Check LEADERSHIP (if weight > 0)
    if category_weights.get(CompetencyCategory.LEADERSHIP, 0) > 0:
        if CompetencyCategory.LEADERSHIP not in categories:
            raise ValidationError(
                "Must have at least one LEADERSHIP competency (LEADERSHIP weight is non-zero)"
            )
    
    # Check FUNCTIONAL (if weight > 0)
    if category_weights.get(CompetencyCategory.FUNCTIONAL, 0) > 0:
        if CompetencyCategory.FUNCTIONAL not in categories:
            raise ValidationError(
                "Must have at least one FUNCTIONAL competency (FUNCTIONAL weight is non-zero)"
            )
 
 
def competency_score(competency: Competency, *, cap_at_100: bool = True) -> float:
    """
    Calculate score for a single competency using NEW method.
    
    This requires knowing the category weight and count, so we need the evaluation.
    
    Formula:
    - Competency % = Category Weight / Count in Category
    - Score = (Actual / Required) × Competency %
    
    Args:
        competency: Competency instance
        cap_at_100: If True, cap achievement ratio at 100%
    
    Returns:
        float: Competency score
    """
    evaluation = competency.evaluation
    
    # Get required and actual levels
    required = float(competency.required_level or 0)
    if required <= 0:
        return 0.0
    
    actual = float(competency.actual_level or 0)
    ratio = actual / required
    
    # Cap at 100% if requested
    if cap_at_100:
        ratio = max(0.0, min(1.0, ratio))
    
    # Get category weight
    category_weights = category_weights_for_evaluation(evaluation)
    
    category_weight = category_weights.get(competency.category, 0.0)
    print(f"DEBUG category_weight: { category_weight}" )
    # Count competencies in this category
    count_in_category = evaluation.competency_set.filter(
        category=competency.category
    ).count()
    
    if count_in_category == 0:
        return 0.0
    
    # Calculate competency percentage
    competency_percentage = category_weight / count_in_category
    print(f"DEBUG competency_percentage: { competency_percentage}" )
    # Calculate score
    score = ratio * competency_percentage
    
    return _round2(score)
 
def sum_competencies_score(evaluation: Evaluation, *, cap_at_100: bool = True) -> float:
    subTotal = 0.0
    
    for comp in evaluation.competency_set.all():
        subTotal += competency_score(comp, cap_at_100=cap_at_100)
    
    return _round2(subTotal)
def calculate_competencies_score(
    evaluation: Evaluation, 
    *, 
    cap_at_100: bool = True,
    return_breakdown: bool = False
) -> float | dict:
    """
    Calculate competencies score using SUM × COUNT × WEIGHT method.
    
    FORMULA (from Excel):
    Category Score = (Sum of Actual Levels) × Count × (Category Weight / 100)
    Total = Sum of all category scores
    
    Example from Excel:
        CORE (40% weight, 5 competencies):
        - Sum actuals: 20
        - Score: 20 × 5 × (40/100) = 40%
        
        FUNCTIONAL (60% weight, 5 competencies):
        - Sum actuals: 14
        - Score: 14 × 5 × (60/100) = 42%
        
        Total: 40 + 42 = 82%
    
    Args:
        evaluation: Evaluation instance
        cap_at_100: Not used in this formula (kept for compatibility)
        return_breakdown: If True, return detailed breakdown by category
    
    Returns:
        float: Total competencies score (as percentage)
        OR dict: Detailed breakdown if return_breakdown=True
    """
    competencies = evaluation.competency_set.only(
        'competence_id', 'category', 'name', 'required_level', 'actual_level'
    ).all()
    
    if not competencies.exists():
        if return_breakdown:
            return {
                'total': 0.0,
                'weighted': 0.0,
                'core_score': 0.0,
                'leadership_score': 0.0,
                'functional_score': 0.0,
                'breakdown': []
            }
        return 0.0
    
    # Get category weights from evaluation snapshot
    category_weights = category_weights_for_evaluation(evaluation)
    
    # Group by category and sum actuals/requireds
    category_data = {
        CompetencyCategory.CORE: {
            'sum_actual': Decimal('0'),
            'sum_required': Decimal('0'),
            'count': 0,
            'competencies': []
        },
        CompetencyCategory.LEADERSHIP: {
            'sum_actual': Decimal('0'),
            'sum_required': Decimal('0'),
            'count': 0,
            'competencies': []
        },
        CompetencyCategory.FUNCTIONAL: {
            'sum_actual': Decimal('0'),
            'sum_required': Decimal('0'),
            'count': 0,
            'competencies': []
        },
    }
    
    # First pass: sum actuals and requireds per category
    for comp in competencies:
        category = comp.category
        required = _d(comp.required_level)
        actual = _d(comp.actual_level)
        
        # Skip if required level is 0 (not applicable)
        if required == 0:
            continue
        
        category_data[category]['sum_actual'] += actual
        category_data[category]['sum_required'] += required
        category_data[category]['count'] += 1
        category_data[category]['competencies'].append(comp)
    
    # Second pass: calculate category scores
    category_scores = {
        CompetencyCategory.CORE: Decimal('0.00'),
        CompetencyCategory.LEADERSHIP: Decimal('0.00'),
        CompetencyCategory.FUNCTIONAL: Decimal('0.00')
    }
    
    breakdown = []
    total_score = Decimal('0.00')
    
    for category, data in category_data.items():
        sum_actual = data['sum_actual']
        count = data['count']
        
        # Skip if no competencies in this category
        if count == 0:
            continue
        
        # Get category weight (as percentage, e.g., 40 for 40%)
        category_weight = _d(category_weights.get(category, 0))
        
        # Calculate category score using the formula:
        # Category Score = (Sum of Actuals) × Count × (Category Weight / 100)
        category_score = sum_actual * _d(count) * (category_weight / Decimal('100'))
        
        category_scores[category] = category_score
        total_score += category_score
        
        # Add to breakdown if requested
        if return_breakdown:
            for comp in data['competencies']:
                breakdown.append({
                    'name': comp.name,
                    'category': category,
                    'required_level': int(comp.required_level),
                    'actual_level': int(comp.actual_level),
                })
            
            # Category summary
            breakdown.append({
                'category_summary': category,
                'count': count,
                'sum_actual': float(sum_actual),
                'category_weight': _round2(category_weight),
                'category_score': _round2(category_score),
                'formula': f"{float(sum_actual)} × {count} × ({_round2(category_weight)}/100) = {_round2(category_score)}"
            })
    
    # Round to 2 decimal places
    total_score = total_score.quantize(CENT)
     
    # Apply competency weight percentage for final evaluation
    comp_weight_pct = _d(evaluation.comp_weight_pct or 0)
    weighted_score = (total_score * comp_weight_pct / Decimal('100')).quantize(CENT)
    
    if return_breakdown:
        return {
            'total': _round2(total_score),
            'weighted': _round2(weighted_score),
            'core_score': _round2(category_scores[CompetencyCategory.CORE]),
            'leadership_score': _round2(category_scores[CompetencyCategory.LEADERSHIP]),
            'functional_score': _round2(category_scores[CompetencyCategory.FUNCTIONAL]),
            'breakdown': breakdown
        }
    
    return _round2(weighted_score)


def sum_competencies_score(
    evaluation: Evaluation, 
    *, 
    cap_at_100: bool = True,
    return_breakdown: bool = False
) -> float | dict:
    """
    Calculate competencies score using SUM × COUNT × WEIGHT method.
    
    FORMULA (from Excel):
    Category Score = (Sum of Actual Levels) × Count × (Category Weight / 100)
    Total = Sum of all category scores
    
    Example from Excel:
        CORE (40% weight, 5 competencies):
        - Sum actuals: 20
        - Score: 20 × 5 × (40/100) = 40%
        
        FUNCTIONAL (60% weight, 5 competencies):
        - Sum actuals: 14
        - Score: 14 × 5 × (60/100) = 42%
        
        Total: 40 + 42 = 82%
    
    Args:
        evaluation: Evaluation instance
        cap_at_100: Not used in this formula (kept for compatibility)
        return_breakdown: If True, return detailed breakdown by category
    
    Returns:
        float: Total competencies score (as percentage)
        OR dict: Detailed breakdown if return_breakdown=True
    """
    competencies = evaluation.competency_set.only(
        'competence_id', 'category', 'name', 'required_level', 'actual_level'
    ).all()
    
    if not competencies.exists():
        if return_breakdown:
            return {
                'total': 0.0,
                'weighted': 0.0,
                'core_score': 0.0,
                'leadership_score': 0.0,
                'functional_score': 0.0,
                'breakdown': []
            }
        return 0.0
    
    # Get category weights from evaluation snapshot
    category_weights = category_weights_for_evaluation(evaluation)
    
    # Group by category and sum actuals/requireds
    category_data = {
        CompetencyCategory.CORE: {
            'sum_actual': Decimal('0'),
            'sum_required': Decimal('0'),
            'count': 0,
            'competencies': []
        },
        CompetencyCategory.LEADERSHIP: {
            'sum_actual': Decimal('0'),
            'sum_required': Decimal('0'),
            'count': 0,
            'competencies': []
        },
        CompetencyCategory.FUNCTIONAL: {
            'sum_actual': Decimal('0'),
            'sum_required': Decimal('0'),
            'count': 0,
            'competencies': []
        },
    }
    
    # First pass: sum actuals and requireds per category
    for comp in competencies:
        category = comp.category
        required = _d(comp.required_level)
        actual = _d(comp.actual_level)
        
        # Skip if required level is 0 (not applicable)
        if required == 0:
            continue
        
        category_data[category]['sum_actual'] += actual
        category_data[category]['sum_required'] += required
        category_data[category]['count'] += 1
        category_data[category]['competencies'].append(comp)
    
    # Second pass: calculate category scores
    category_scores = {
        CompetencyCategory.CORE: Decimal('0.00'),
        CompetencyCategory.LEADERSHIP: Decimal('0.00'),
        CompetencyCategory.FUNCTIONAL: Decimal('0.00')
    }
    
    breakdown = []
    total_score = Decimal('0.00')
    
    for category, data in category_data.items():
        sum_actual = data['sum_actual']
        count = data['count']
        
        # Skip if no competencies in this category
        if count == 0:
            continue
        
        # Get category weight (as percentage, e.g., 40 for 40%)
        category_weight = _d(category_weights.get(category, 0))
        
        # Calculate category score using the formula:
        # Category Score = (Sum of Actuals) × Count × (Category Weight / 100)
        category_score = sum_actual * _d(count) * (category_weight / Decimal('100'))
        
        category_scores[category] = category_score
        total_score += category_score
        
        # Add to breakdown if requested
        if return_breakdown:
            for comp in data['competencies']:
                breakdown.append({
                    'name': comp.name,
                    'category': category,
                    'required_level': int(comp.required_level),
                    'actual_level': int(comp.actual_level),
                })
            
            # Category summary
            breakdown.append({
                'category_summary': category,
                'count': count,
                'sum_actual': float(sum_actual),
                'category_weight': _round2(category_weight),
                'category_score': _round2(category_score),
                'formula': f"{float(sum_actual)} × {count} × ({_round2(category_weight)}/100) = {_round2(category_score)}"
            })
    
    # Round to 2 decimal places
    total_score = total_score.quantize(CENT)
    

     
    if return_breakdown:
        return {
            'total': _round2(total_score),
            'core_score': _round2(category_scores[CompetencyCategory.CORE]),
            'leadership_score': _round2(category_scores[CompetencyCategory.LEADERSHIP]),
            'functional_score': _round2(category_scores[CompetencyCategory.FUNCTIONAL]),
            'breakdown': breakdown
        }
    
    return _round2(total_score)