from django.core.management.base import BaseCommand
from evaluation_app.models import WeightsConfiguration

class Command(BaseCommand):
    help = 'Add EXECUTIVE weight configuration'

    def handle(self, *args, **options):
        obj, created = WeightsConfiguration.objects.get_or_create(
            level_name='EXECUTIVE',
            defaults={
                'core_weight': 20,
                'leadership_weight': 80,
                'functional_weight': 0,
                'competency_weight': 20,
                'objective_weight': 80,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ EXECUTIVE weights added'))
        else:
            self.stdout.write(self.style.WARNING('EXECUTIVE weights already exist'))