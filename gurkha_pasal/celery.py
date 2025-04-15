import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurkha_pasal.settings')
app = Celery('gurkha_pasal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()