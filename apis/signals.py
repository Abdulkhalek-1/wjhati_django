import logging
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from apis.tasks import send_fcm_notification
from .models import Booking, Chat, Transaction, Transfer, Bonus, Wallet, CasheBooking, Trip, Notification, FCMToken

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'wallet'):
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=Bonus)
def handle_bonus_creation(sender, instance, created, **kwargs):
    if not created or instance.processed:
        return

    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=instance.user)
            wallet.credit(instance.amount)
            instance.processed = True
            instance.save(update_fields=['processed'])
    except Wallet.DoesNotExist:
        raise ObjectDoesNotExist(f"المستخدم {instance.user.username} ليس لديه محفظة")

@receiver(post_save, sender=Transaction)
def update_wallet_balance(sender, instance, created, **kwargs):
    if not created:
        return

    wallet = instance.wallet
    try:
        with transaction.atomic():
            if instance.transaction_type == 'charge':
                wallet.credit(instance.amount)
            elif instance.transaction_type in ['withdraw', 'payment']:
                wallet.debit(instance.amount)
    except Exception as e:
        raise

@receiver(post_save, sender=Transfer)
def auto_process_transfer(sender, instance, created, **kwargs):
    if created:
        try:
            instance.process_transfer()
        except Exception as e:
            logger.error(f"فشل في معالجة التحويل {instance.id}: {e}")

@receiver(post_save, sender=User)
def create_user_chat(sender, instance, created, **kwargs):
    """إنشاء محادثة تلقائية للمستخدم الجديد"""
    if created:
        try:
            chat = Chat.objects.create(title=f"Chat for {instance.username}")
            chat.participants.add(instance)
            logger.info(f"تم إنشاء محادثة جديدة للمستخدم {instance.username}")
        except Exception as e:
            logger.error(f"فشل في إنشاء محادثة للمستخدم {instance.username}: {e}")

@receiver(post_save, sender=Trip)
def mark_driver_unavailable(sender, instance, created, **kwargs):
    if created and instance.driver and instance.status != 'completed':
        instance.driver.is_available = False
        instance.driver.save(update_fields=['is_available'])


@receiver(post_save, sender=Notification)
def on_notification_created(sender, instance, created, **kwargs):
    if created:
        # ترسل الإشعار مباشرة بعد إنشاء السجل
        send_fcm_notification(
            user=instance.user,
            title=instance.title,
            message=instance.message,
            data={
                "notification_type": getattr(instance, "notification_type", ""),
                "related_object_id": getattr(instance, "related_object_id", "")
            }
        )

@receiver([post_save, post_delete], sender=Booking)
def update_trip_availability(sender, instance, **kwargs):
    instance.trip.update_availability()