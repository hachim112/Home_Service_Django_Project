import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Home_Service_Django_Project.settings')

application = get_wsgi_application()
