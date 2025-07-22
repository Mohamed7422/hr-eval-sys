# api/index.py
import os
import sys
from pathlib import Path

from serverless_wsgi import handle_request
from django.core.wsgi import get_wsgi_application

# Add the project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# 1) Point Django at your settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hr_evaluation.settings")

# 2) Load WSGI app once
application = get_wsgi_application()

def handler(event, context):
    # 3) Adapt the incoming Vercel (or any serverless) request to Django
    return handle_request(application, event, context)
