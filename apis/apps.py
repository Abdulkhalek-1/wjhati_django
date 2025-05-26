# apis/apps.py
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)

class ApisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apis'

    def ready(self):
        self._load_signals()

    def _load_signals(self):
        try:
            import apis.signals
            logger.info("✅ Notification signals loaded successfully")
        except Exception as e:
            logger.error("❌ Failed to load notification signals", exc_info=True)

