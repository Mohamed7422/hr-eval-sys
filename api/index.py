# api/index.py
import os
from serverless_wsgi import handle_request
from django.core.wsgi import get_wsgi_application

# 1) Point Django at your settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hr_evaluation.settings")

# 2) Load WSGI app once
application = get_wsgi_application()

def handler(request, response):
    # 3) Adapt the incoming Vercel request to Django
    return handle_request(application, request, response)
