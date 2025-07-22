# api/index.py
import os
import sys
from pathlib import Path

from serverless_wsgi import handle_request
from django.core.wsgi import get_wsgi_application

# 0) Make sure your project root is on the path if index.py lives in a subfolder
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# 1) Point Django at your settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hr_evaluation.settings")

# 2) Load the WSGI app once
application = get_wsgi_application()

# 3) This is the entrypoint Vercel will invoke
def handle_request(django_app, event, context):
 
    return handle_request(application, event, context)
