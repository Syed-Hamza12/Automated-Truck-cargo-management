import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'truck_Cargo.settings')

app = Celery('truck_Cargo')

app.conf.task_default_rate_limit = '1/m'
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()