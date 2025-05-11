import threading
import logging
from django.apps import AppConfig
from django.core.management import call_command

logger = logging.getLogger(__name__)

class ApisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apis'

    def ready(self):
        # تحميل الإشارات
        try:
            import apis.signals
            logger.info("Notification signals loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load signals: {str(e)}", exc_info=True)

        # منع التكرار في حالة إعادة تحميل التطبيق
        if hasattr(self, 'hybrid_scheduler_started'):
            return
        self.hybrid_scheduler_started = True

        # بدء تشغيل الأمر في خيط منفصل
        def start_hybrid_scheduler():
            try:
                call_command('dbscan_clustering', '--eps', '0.1', '--min_samples', '3')
            except Exception as e:
                logger.error(f"Error starting hybrid scheduler: {e}", exc_info=True)

        threading.Thread(target=start_hybrid_scheduler, daemon=True).start()
        logger.info("Hybrid scheduler thread started.")
