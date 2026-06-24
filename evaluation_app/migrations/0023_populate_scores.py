# evaluation_app/migrations/XXXX_populate_evaluation_scores.py

from django.db import migrations
from decimal import Decimal, ROUND_HALF_UP


def _d(x):
    return Decimal(str(x))


def _round2(x):
    return float(Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def calculate_objectives_score(evaluation):
    """Calculate raw objectives score."""
    subtotal = Decimal("0")
    
    for obj in evaluation.objective_set.all():
        try:
            target = _d(float(obj.target)) if obj.target else Decimal("0")
            if target <= 0:
                continue
            
            achieved = _d(float(obj.achieved)) if obj.achieved else Decimal("0")
            ratio = achieved / target
            
            # Cap at 100%
            if ratio < 0:
                ratio = Decimal("0")
            if ratio > 1:
                ratio = Decimal("1")
            
            weight_percent = _d(obj.weight) if obj.weight is not None else Decimal("0")
            subtotal += ratio * weight_percent
        except Exception:
            continue
    
    return _round2(subtotal.quantize(Decimal('0.01')))


def calculate_competencies_score(evaluation):
    """Calculate raw competencies score."""
    from evaluation_app.models import CompetencyCategory
    
    competencies = evaluation.competency_set.all()
    
    if not competencies.exists():
        return 0.0
    
    # Get category weights
    category_weights = {
        CompetencyCategory.CORE: float(evaluation.comp_core_pct or 0.0),
        CompetencyCategory.LEADERSHIP: float(evaluation.comp_leadership_pct or 0.0),
        CompetencyCategory.FUNCTIONAL: float(evaluation.comp_functional_pct or 0.0),
    }
    
    # Group by category
    category_data = {
        CompetencyCategory.CORE: {'sum_actual': Decimal('0'), 'count': 0},
        CompetencyCategory.LEADERSHIP: {'sum_actual': Decimal('0'), 'count': 0},
        CompetencyCategory.FUNCTIONAL: {'sum_actual': Decimal('0'), 'count': 0},
    }
    
    for comp in competencies:
        required = _d(comp.required_level)
        if required == 0:
            continue
        
        actual = _d(comp.actual_level)
        category_data[comp.category]['sum_actual'] += actual
        category_data[comp.category]['count'] += 1
    
    # Calculate scores
    total_score = Decimal('0.00')
    
    for category, data in category_data.items():
        count = data['count']
        if count == 0:
            continue
        
        sum_actual = data['sum_actual']
        category_weight = _d(category_weights.get(category, 0))
        
        # Category Score = (Sum Actuals) × Count × (Category Weight / 100)
        category_score = sum_actual * _d(count) * (category_weight / Decimal('100'))
        total_score += category_score
    
    return _round2(total_score.quantize(Decimal('0.01')))


def populate_scores(apps, schema_editor):
    """Populate objectives_score and competencies_score for existing evaluations."""
    Evaluation = apps.get_model('evaluation_app', 'Evaluation')
    
    count = 0
    batch = []
    
    for evaluation in Evaluation.objects.all():
        # Calculate raw scores
        objectives_score = calculate_objectives_score(evaluation)
        competencies_score = calculate_competencies_score(evaluation)
        
        # Calculate final score
        obj_weight = Decimal(str(evaluation.obj_weight_pct or 0))
        comp_weight = Decimal(str(evaluation.comp_weight_pct or 0))
        
        objectives_contribution = (Decimal(str(objectives_score)) * obj_weight / Decimal('100'))
        competencies_contribution = (Decimal(str(competencies_score)) * comp_weight / Decimal('100'))
        
        final_score = objectives_contribution + competencies_contribution
        final_score = final_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Update evaluation
        evaluation.objectives_score = objectives_score
        evaluation.competencies_score = competencies_score
        evaluation.score = float(final_score)
        batch.append(evaluation)
        
        count += 1
        
        # Bulk update every 100 evaluations
        if len(batch) >= 100:
            Evaluation.objects.bulk_update(
                batch,
                ['objectives_score', 'competencies_score', 'score']
            )
            batch = []
            print(f"Populated {count} evaluations...")
    
    # Update remaining
    if batch:
        Evaluation.objects.bulk_update(
            batch,
            ['objectives_score', 'competencies_score', 'score']
        )
    
    print(f"✅ Successfully populated scores for {count} evaluations")


def reverse_populate(apps, schema_editor):
    """Reverse migration - set scores to NULL."""
    Evaluation = apps.get_model('evaluation_app', 'Evaluation')
    Evaluation.objects.all().update(
        objectives_score=None,
        competencies_score=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation_app', '0022_alter_evaluation_score'),  
    ]

    operations = [
        migrations.RunPython(populate_scores, reverse_populate),
    ]