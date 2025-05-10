import threading
import time
import logging
from django.apps import AppConfig
from django.core.management import call_command

logger = logging.getLogger(__name__)

class ApisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apis'

    def ready(self):
        # تفعيل الإشارات مع معالجة الأخطاء
        try:
            import apis.signals
            logger.info("Notification signals loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load signals: {str(e)}", exc_info=True)
        # منع بدء المخطط أكثر من مرة
        if hasattr(self, 'scheduler_started'):
            return
            
        setattr(self, 'scheduler_started', True)
        
        def run_scheduler():
            while True:
                try:
                    logger.info("Running DBSCAN clustering...")
                    call_command('dbscan_clustering', '--eps', '0.1', '--min_samples', '3')
                except Exception as e:
                    logger.error(f"[DBSCAN Scheduler] Error: {e}", exc_info=True)
                finally:
                    time.sleep(300)  # 5 دقائق

        try:
            t = threading.Thread(
                target=run_scheduler,
                daemon=True,
                name="DBSCAN_Scheduler"
            )
            t.start()
            logger.info("DBSCAN scheduler thread started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler thread: {str(e)}", exc_info=True)