from evaluation_app.models import Evaluation
from evaluation_app.services.evaluation_math import calculate_evaluation_score

print("Populating scores for existing evaluations...")

count = 0
for evaluation in Evaluation.objects.all():
    calculate_evaluation_score(evaluation, persist=True)
    count += 1
    if count % 10 == 0:
        print(f"Processed {count} evaluations...")

print(f"✅ Done! Updated {count} evaluations.")




















































