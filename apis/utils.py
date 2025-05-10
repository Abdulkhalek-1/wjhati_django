import logging
from pyfcm import FCMNotification
from django.conf import settings

from apis.models import FCMToken

logger = logging.getLogger(__name__)
try:
    FCM_API_KEY = getattr(settings, 'FCM_API_KEY', None)
    if not FCM_API_KEY:
        raise ValueError("FCM_API_KEY not found in settings")
        
    push_service = FCMNotification(api_key=FCM_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize FCM service: {str(e)}")
    push_service = None

def send_notification_to_user(user, title, message, data=None):
    if push_service is None:
        logger.error("FCM service not initialized - cannot send notification")
        return None
    """
    إرسال إشعار FCM إلى مستخدم معين
    
    :param user: مستخدم الهدف
    :param title: عنوان الإشعار
    :param message: محتوى الإشعار
    :param data: بيانات إضافية (اختياري)
    :return: نتيجة الإرسال أو None في حالة الفشل
    """
    try:
        # استرجاع التوكنز في استعلام واحد فقط
        tokens = list(FCMToken.objects.filter(user=user).values_list("token", flat=True))
        
        if not tokens:
            logger.warning(f"No FCM tokens found for user {user.id}")
            return None
            
        kwargs = {
            'registration_ids': tokens,
            'message_title': title,
            'message_body': message,
        }
        
        if data:
            kwargs['data_message'] = data
            
        result = push_service.notify_multiple_devices(**kwargs)
        
        logger.info(f"Notification sent to user {user.id}. Result: {result}")
        
        # تسجيل التوكنز الفاشلة لإزالتها لاحقاً
        if result and 'results' in result:
            for i, res in enumerate(result['results']):
                if res.get('error') in ['InvalidRegistration', 'NotRegistered']:
                    FCMToken.objects.filter(token=tokens[i]).delete()
                    logger.info(f"Removed invalid FCM token: {tokens[i]}")
                    
        return result
        
    except Exception as e:
        logger.error(f"Failed to send notification to user {user.id}: {str(e)}", exc_info=True)
        return None