import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_evaluation.settings')

application = get_wsgi_application()

# Vercel needs the app to be named 'app'
app = application