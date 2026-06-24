from django.apps import AppConfig


class EvaluationAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evaluation_app'

    def ready(self):
        import evaluation_app.signals