import logging
from django.db import transaction
from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

from apis.tasks import send_fcm_notification
from .models import Booking, Chat, Transaction, Transfer, Bonus, Wallet, CasheBooking, Trip
from .models import Notification, FCMToken
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class WalletSignals:
    """إشارات متعلقة بالمحفظة الإلكترونية"""
    
    @receiver(post_save, sender=User)
    def create_user_wallet(sender, instance, created, **kwargs):
        """إنشاء محفظة تلقائية للمستخدم الجديد"""
        if created and not hasattr(instance, 'wallet'):
            try:
                Wallet.objects.create(user=instance, balance=0.00)
                logger.info(f"تم إنشاء محفظة جديدة للمستخدم {instance.username}")
            except Exception as e:
                logger.error(f"فشل في إنشاء محفظة للمستخدم {instance.username}: {e}")

    @receiver(post_save, sender=Bonus)
    def handle_bonus_creation(sender, instance, created, **kwargs):
        """تحديث رصيد المحفظة عند إضافة مكافأة"""
        if not created or hasattr(instance, 'processed'):
            return
            
        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=instance.user)
                if instance.amount <= 0:
                    raise ValueError("قيمة المكافأة غير صالحة")
                    
                wallet.balance += instance.amount
                wallet.save(update_fields=['balance'])
                instance.processed = True
                instance.save(update_fields=['processed'])
                logger.info(f"تمت إضافة مكافأة {instance.amount} لمحفظة {instance.user.username}")
                
        except Wallet.DoesNotExist:
            logger.error(f"المستخدم {instance.user.username} ليس لديه محفظة")
            raise ObjectDoesNotExist(f"المستخدم {instance.user.username} ليس لديه محفظة")
        except Exception as e:
            logger.error(f"فشل تحديث المحفظة للمكافأة {instance.id}: {e}")
            raise

    @receiver(post_save, sender=Transaction)
    def update_wallet_balance(sender, instance, **kwargs):
        """تحديث رصيد المحفظة بناءً على نوع المعاملة"""
        wallet = instance.wallet
        try:
            with transaction.atomic():
                if instance.transaction_type == 'charge':
                    wallet.balance += instance.amount
                elif instance.transaction_type in ['withdraw', 'payment']:
                    if wallet.balance >= instance.amount:
                        wallet.balance -= instance.amount
                    else:
                        raise ValueError("رصيد غير كافٍ")
                wallet.save(update_fields=['balance'])
                logger.info(f"تم تحديث رصيد المحفظة {wallet.id} للعملية {instance.id}")
        except Exception as e:
            logger.error(f"فشل تحديث رصيد المحفظة للعملية {instance.id}: {e}")
            raise

    @receiver(post_save, sender=Transfer)
    def process_transfer(sender, instance, **kwargs):
        """معالجة التحويل بين المحافظ"""
        try:
            with transaction.atomic():
                from_wallet = Wallet.objects.select_for_update().get(pk=instance.from_wallet.pk)
                to_wallet = Wallet.objects.select_for_update().get(pk=instance.to_wallet.pk)
                
                if from_wallet.balance >= instance.amount:
                    from_wallet.balance -= instance.amount
                    to_wallet.balance += instance.amount
                    from_wallet.save(update_fields=['balance'])
                    to_wallet.save(update_fields=['balance'])
                    instance.status = Transfer.Status.COMPLETED
                    instance.save(update_fields=['status'])
                    logger.info(f"تم تحويل {instance.amount} من {from_wallet.id} إلى {to_wallet.id}")
                else:
                    instance.status = Transfer.Status.FAILED
                    instance.save(update_fields=['status'])
                    raise ValueError("رصيد غير كافٍ في محفظة المرسل")
        except Exception as e:
            logger.error(f"فشل في معالجة التحويل {instance.id}: {e}")
            raise


#     هذي الاشار مخصصة لتغيير حالة المستخدم بحيث اذا تم اضافته الى رحلة يتم تغيير حالة
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