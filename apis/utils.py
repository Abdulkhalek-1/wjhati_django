from django.conf import settings
import requests

from apis.models import FCMToken
def send_fcm_notification(user, title, message, data=None):
    tokens = FCMToken.objects.filter(user=user).values_list('token', flat=True)
    if not tokens:
        print("🚫 لا توجد توكنات FCM للمستخدم.")
        return

    print("📤 يتم إرسال إشعار إلى Firebase...")
    
    payload = {
        "registration_ids": list(tokens),
        "notification": {
            "title": title,
            "body": message
        },
        "data": data or {}
    }

    headers = {
        "Authorization": f"key={settings.FCM_SERVER_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://fcm.googleapis.com/fcm/send", json=payload, headers=headers)
    
    print("📬 رد Firebase:", response.status_code, response.text)
    return response.json()
