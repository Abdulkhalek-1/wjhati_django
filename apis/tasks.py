from firebase_admin import messaging
from apis.models import FCMToken
import apis.firebase  # للتأكد من تهيئة Firebase

def send_fcm_notification(user, title, message, data=None):
    tokens = FCMToken.objects.filter(user=user).values_list('token', flat=True)
    if not tokens:
        print("🚫 لا توجد توكنات FCM للمستخدم.")
        return

    # جهّز dict للـ data مع تحويل القيم إلى نص واستبعاد None
    clean_data = {}
    if data:
        for key, value in data.items():
            if value is not None:
                clean_data[key] = str(value)

    for token in tokens:
        msg = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message,
            ),
            token=token,
            data=clean_data    # الآن جميع القيم نصّيّة
        )
        try:
            print("🚀 إرسال إشعار عبر Firebase Admin SDK...")
            response = messaging.send(msg)
            print(f"✅ تم الإرسال: {response}")
        except Exception as e:
            print(f"❌ فشل إرسال الإشعار: {e}")
