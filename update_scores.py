import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_evaluation.settings')
django.setup()

# Now import your models
from evaluation_app.models import Evaluation
from evaluation_app.services.evaluation_math import calculate_evaluation_score

print("Starting to update evaluation scores...")

count = 0
for evaluation in Evaluation.objects.all():
    calculate_evaluation_score(evaluation, persist=True)
    count += 1
    print(f"Updated evaluation {count}: {evaluation.evaluation_id}")

print(f"\nAll evaluation scores updated! Total: {count}")