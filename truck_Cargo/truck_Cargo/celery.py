import os
from celery import Celery

# 1. Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'truck_Cargo.settings')

app = Celery('truck_Cargo')

# 2. LOAD DJANGO SETTINGS FIRST 
# This pulls in your CELERY_BROKER_URL = 'redis://redis:6379/0'
app.config_from_object('django.conf:settings', namespace='CELERY')

# 3. Apply manual overrides AFTER loading settings
app.conf.task_default_rate_limit = '1/m'

# 4. Discover tasks
app.autodiscover_tasks()