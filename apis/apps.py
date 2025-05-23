import os
import threading
import logging
from django.apps import AppConfig
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger(__name__)

class ApisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apis'

    def ready(self):
        self._load_signals()
        self._start_trip_scheduler()

    def _load_signals(self):
        try:
            import apis.signals
            logger.info("✅ Notification signals loaded successfully")
        except Exception as e:
            logger.error("❌ Failed to load notification signals", exc_info=True)

    def _start_trip_scheduler(self):
        # تأكد من أن الكود لا يعمل أثناء المايجريشن أو في أوامر أخرى غير runserver
        if os.environ.get('RUN_MAIN') != 'true':
            return

        def run_scheduler():
            try:
                logger.info("📦 Starting intelligent trip scheduler using DBSCAN...")
                call_command('dbscan_clustering', '--min_cluster_size', '3')
            except Exception as e:
                logger.error("❌ Failed to start DBSCAN scheduler", exc_info=True)

        threading.Thread(target=run_scheduler, daemon=True).start()
        logger.info("✅ DBSCAN scheduler thread started.")
