# File: apis/retry_queue.py
import logging
from datetime import timedelta
from django.utils.timezone import now

logger = logging.getLogger(__name__)

retry_registry = {}
RETRY_TIMEOUT_MINUTES = 60

def add_to_retry_queue(item):
    now_time = now()
    last_retry = retry_registry.get(item.id)
    if last_retry and (now_time - last_retry).total_seconds() < RETRY_TIMEOUT_MINUTES * 60:
        return

    retry_registry[item.id] = now_time
    try:
        logger.info(f"🔁 إضافة العنصر {item.id} إلى قائمة المحاولات.")
    except Exception as e:
        logger.error(f"❌ فشل إضافة العنصر {item.id} إلى قائمة المحاولات: {e}")

