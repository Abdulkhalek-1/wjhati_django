from pyfcm import FCMNotification
from .models import FCMToken

# مفتاح السيرفر الخاص بـ FCM (من Firebase Console)
FCM_API_KEY = "ضع مفتاح FCM هنا"

push_service = FCMNotification(api_key=FCM_API_KEY)

def send_notification_to_user(user, title, message):
    tokens = FCMToken.objects.filter(user=user).values_list("token", flat=True)
    if tokens:
        result = push_service.notify_multiple_devices(
            registration_ids=list(tokens),
            message_title=title,
            message_body=message
        )
        return result
    return None
