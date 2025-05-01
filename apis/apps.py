from django.apps import AppConfig
import threading
import time
from django.apps import AppConfig
from django.core.management import call_command
class ApisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apis'
    def ready(self):
        if hasattr(self, 'scheduler_started'):
            return
        setattr(self, 'scheduler_started', True)

        def run_scheduler():
            # انتظر قبل التشغيل الأول إن أحببت
            while True:
                try:
                    # استدعاء الأمر الخاص بك
                    call_command('dbscan_clustering', '--eps', '0.1', '--min_samples', '3')
                except Exception as e:
                    # هنا يمكنك تسجيل الخطأ في لوج أو إرسال تنبيه
                    print(f"[DBSCAN Scheduler] Error: {e}")
                # انتظر ساعة (3600 ثانية) ثم أعد التشغيل
                time.sleep(3600)

        t = threading.Thread(target=run_scheduler, daemon=True)
        t.start()
