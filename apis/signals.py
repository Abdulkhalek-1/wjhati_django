import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from .utils import *
from django.contrib.auth.models import User
from .models import Transaction, Transfer, Bonus, Wallet, CasheBooking, Trip, Driver,Rating
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Bonus)
def update_wallet_on_bonus(sender, instance, created, **kwargs):
    """
    تحديث رصيد المحفظة عند إنشاء مكافأة جديدة:
      1. التأكد من أن المكافأة جديدة.
      2. الحصول على محفظة المستخدم مع قفل الصف لتجنب التعارض.
      3. التحقق من أن قيمة المكافأة أكبر من الصفر.
      4. زيادة الرصيد وحفظ التحديث.
    """
    if created:
        try:
            with transaction.atomic():
                user_wallet = Wallet.objects.select_for_update().get(user=instance.user)
                if instance.amount <= 0:
                    raise ValueError("قيمة المكافأة يجب أن تكون أكبر من الصفر.")
                user_wallet.balance += instance.amount
                user_wallet.save()
                logger.info(f"تمت إضافة مكافأة بمبلغ {instance.amount} للمحفظة الخاصة بالمستخدم {instance.user.username}.")
        except Wallet.DoesNotExist:
            logger.error(f"لم يتم العثور على محفظة للمستخدم {instance.user}.")
            raise ObjectDoesNotExist(f"المستخدم {instance.user} ليس لديه محفظة.")
        except Exception as e:
            logger.error(f"فشل تحديث المحفظة للمكافأة {instance.id}: {e}")
            raise

@receiver(post_save, sender=Transaction)
def update_wallet_balance(sender, instance, **kwargs):
    """
    تحديث رصيد المحفظة بناءً على نوع العملية:
      - عند الشحن (charge) يتم زيادة الرصيد.
      - عند السحب أو الدفع (withdraw, payment) يتم خصم المبلغ إذا كان الرصيد كافٍ.
    """
    wallet = instance.wallet
    try:
        with transaction.atomic():
            if instance.transaction_type == 'charge':
                wallet.balance += instance.amount
            elif instance.transaction_type in ['withdraw', 'payment']:
                if wallet.balance >= instance.amount:
                    wallet.balance -= instance.amount
                else:
                    raise ValueError("رصيد غير كافٍ.")
            wallet.save()
            logger.info(f"تم تحديث رصيد المحفظة {wallet.id} للعملية {instance.id}.")
    except Exception as e:
        logger.error(f"فشل تحديث رصيد المحفظة للعملية {instance.id}: {e}")
        raise

@receiver(post_save, sender=Transfer)
def update_wallets_balance(sender, instance, **kwargs):
    """
    عند إنشاء عملية تحويل، يتم:
      1. الحصول على محفظة المرسل والمستقبل مع قفل الصف.
      2. التحقق من أن محفظة المرسل تحتوي على رصيد كافٍ.
      3. خصم المبلغ من محفظة المرسل وإضافته لمحفظة المستقبل.
    """
    try:
        with transaction.atomic():
            from_wallet = Wallet.objects.select_for_update().get(pk=instance.from_wallet.pk)
            to_wallet = Wallet.objects.select_for_update().get(pk=instance.to_wallet.pk)
            amount = instance.amount

            if from_wallet.balance >= amount:
                from_wallet.balance -= amount
                to_wallet.balance += amount
                from_wallet.save()
                to_wallet.save()
                logger.info(f"تم تحويل {amount} من المحفظة {from_wallet.id} إلى المحفظة {to_wallet.id}.")
            else:
                raise ValueError("رصيد غير كافٍ في محفظة المرسل.")
    except Exception as e:
        logger.error(f"فشل في معالجة التحويل {instance.id}: {e}")
        raise
# ============================
# إشارات (Signals)
# ============================
@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    عند إنشاء مستخدم جديد، يتم إنشاء محفظة افتراضية له تلقائيًا.
    """
    if created:
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=Trip)
def process_trip_after_save(sender, instance, created, **kwargs):
    """
    عند حفظ نموذج الرحلة، يتم:
    1. التحقق من وجود بيانات route_coordinates.
    2. حساب وإنشاء نقاط التوقف تلقائيًا كل 5 كم.
    3. فحص ودمج الرحلات المشابهة باستخدام خوارزمية Fréchet.
    """
    if instance.route_coordinates:
        compute_trip_stops(instance, stop_interval=5)
        merge_similar_trips(instance)

@receiver(post_save, sender=CasheBooking)
def process_cashe_booking_after_save(sender, instance, created, **kwargs):
    """
    عند إنشاء طلب حجز مسبق (CasheBooking) يتم معالجة الطلب:
    - إذا كان الطلب جديدًا يتم استدعاء دالة process_cashe_booking لنقل البيانات
      إلى جدول الحجوزات وإنشاء رحلة جديدة أو استخدام الرحلة المطابقة.
    """
    if created and instance.status == CasheBooking.Status.PENDING:
        process_cashe_booking(instance)