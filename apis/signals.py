import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from .models import Chat, Transaction, Transfer, Bonus, Wallet, CasheBooking, Trip
from .models import Notification
from .utils import send_notification_to_user

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




@receiver(post_save, sender=Notification)
def send_fcm_notification(sender, instance, created, **kwargs):
    if created:
        try:
            # إعداد بيانات إضافية للإشعار
            data = {
                'notification_id': instance.id,
                'type': instance.notification_type,
                'related_object_id': instance.related_object_id or '',
            }
            
            send_notification_to_user(
                user=instance.user,
                title=instance.title,
                message=instance.message,
                data=data
            )
            
            logger.info(f"Notification {instance.id} sent to user {instance.user.id}")
            
        except Exception as e:
            logger.error(f"Failed to send notification {instance.id}: {str(e)}", exc_info=True)