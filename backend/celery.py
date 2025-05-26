import os
from celery import Celery

# إعداد متغير البيئة الخاص بـ Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# إنشاء كائن Celery
app = Celery('backend')

# تحميل إعدادات Celery من إعدادات Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# اكتشاف المهام تلقائيًا من التطبيقات المثبتة
app.autodiscover_tasks()

# تعريف مهمة Celery للتصحيح
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
